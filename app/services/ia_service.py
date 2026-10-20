import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import estoque_models
from app.schemas import estoque_schemas
from app.services import estoque_service


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()


def _anonimizar_dados_sensiveis_lgpd(texto: str) -> str:
    """Mascara CPF antes de o texto ir para o Gemini ou para o histórico."""
    return re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "***.***.***-** (CPF PROTEGIDO LGPD)", texto)


def _chamar_gemini(prompt: str, temperatura: float) -> Optional[dict]:
    if not settings.GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                # chave no header e não na URL, para não aparecer em log de proxy
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temperatura, "responseMimeType": "application/json"},
                },
            )
        if resp.status_code != 200:
            return None
        texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        resultado = json.loads(texto)
        return resultado if isinstance(resultado, dict) else None
    except Exception:
        return None


def _numero(valor) -> Optional[float]:
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _extrair_crm_e_paciente_regras(relato: str) -> Tuple[Optional[str], Optional[str]]:
    crm = None
    match_crm = re.search(r"\b(?:CRM[-\s/:]*([A-Z]{2}[-\s]*\d{3,7}|\d{3,7}[-\s/]*[A-Z]{0,2}))", relato, re.IGNORECASE)
    if match_crm:
        crm = f"CRM {match_crm.group(1).strip().upper()}"

    paciente = None
    match_pac = re.search(
        r"paciente[:\s]+([A-ZÀ-Úa-zà-ú]+(?:\s+[A-ZÀ-Úa-zà-ú]+){0,3}?)(?=\s+(?:conclu|finaliz|realiz|pelo|dr|crm|utiliz|usou|recebeu|na\s+sala|em\s+|com\s+|\(|cpf|\.|,|$))",
        relato,
        re.IGNORECASE,
    )
    if match_pac:
        paciente = match_pac.group(1).strip().title()
    return crm, paciente


def _extrair_itens_regras(relato: str, produtos_db: List[estoque_models.Produto]) -> List[dict]:
    relato_norm = _normalizar_texto(relato)
    itens_encontrados = []

    for prod in produtos_db:
        nome_norm = _normalizar_texto(prod.nome)
        palavras_chave = [p for p in re.split(r"[\s\-/,]+", nome_norm) if len(p) >= 4 and not p.isdigit()]
        if not palavras_chave:
            palavras_chave = [nome_norm]

        matched_pos = -1
        for kw in palavras_chave:
            if kw in ("injetavel", "emulsao", "sulfato", "citrato", "dissodica", "sodica", "agulhado", "fio"):
                continue
            pos = relato_norm.find(kw)
            if pos != -1:
                matched_pos = pos
                break

        if matched_pos == -1:
            continue

        inicio_janela = max(0, matched_pos - 35)
        fim_janela = min(len(relato_norm), matched_pos + 85)
        trecho_antes = relato_norm[inicio_janela:matched_pos]
        trecho_depois = relato_norm[matched_pos:fim_janela]

        qtd = 1
        nums_antes = re.findall(
            r"\b(\d+)\s*(?:ampola|ampolas|frasco|frascos|unidade|unidades|envelope|envelopes|caixa|caixas|x|de)?\s*$",
            trecho_antes.strip(),
        )
        if nums_antes:
            qtd = int(nums_antes[-1])
        else:
            nums_proximos = re.findall(
                r"\b(\d+)\s*(?:ampola|ampolas|frasco|frascos|unidade|unidades|envelope|envelopes)\b",
                trecho_antes + " " + trecho_depois,
            )
            if nums_proximos:
                qtd = int(nums_proximos[0])

        dose_mg = None
        match_dose = re.search(
            r"(?:dose(?:\s+prescrita)?(?:\s+de)?|aplicado|administrado|bolus(?:\s+de)?|\()\s*(\d+(?:[.,]\d+)?)\s*mg\b",
            trecho_depois,
        )
        if not match_dose:
            match_dose = re.search(r"\b(\d+(?:[.,]\d+)?)\s*mg\b", trecho_depois[len(palavras_chave[0]):])
        if match_dose:
            dose_mg = float(match_dose.group(1).replace(",", "."))

        itens_encontrados.append({
            "produto": prod,
            "quantidade": max(1, qtd),
            "dose_prescrita_mg": dose_mg,
        })

    return itens_encontrados


def _chamar_gemini_relato(relato_seguro: str, catalogo: List[dict]) -> Optional[dict]:
    prompt = f"""
Você é o assistente da farmácia hospitalar do sistema VitalStock.
Leia o relato cirúrgico abaixo e liste os medicamentos usados, usando apenas itens do catálogo.

CATÁLOGO (JSON):
{json.dumps(catalogo, ensure_ascii=False)}

RELATO:
"{relato_seguro}"

Responda só com JSON neste formato:
{{
  "crm_identificado": "CRM do médico ou null",
  "itens": [
    {{"produto_id": 1, "quantidade": 2, "dose_prescrita_mg": 0.05}}
  ]
}}
"""
    return _chamar_gemini(prompt, 0.1)


def interpretar_relato_cirurgico(
    db: Session, request: estoque_schemas.RelatoCirurgicoRequest
) -> estoque_schemas.RelatoCirurgicoResponse:
    relato_seguro = _anonimizar_dados_sensiveis_lgpd(request.relato_texto)
    produtos_db = db.query(estoque_models.Produto).all()
    mapa_produtos = {p.id: p for p in produtos_db}

    catalogo = [
        {
            "id": p.id,
            "nome": p.nome,
            "controlado": bool(p.controlado),
            "dose_maxima_mg": p.dose_maxima,
            "saldo_atual": p.saldo_atual,
        }
        for p in produtos_db
    ]

    # o nome do paciente é identificado localmente e não vai para o Gemini
    crm_regras, paciente_identificado = _extrair_crm_e_paciente_regras(relato_seguro)
    relato_para_llm = relato_seguro
    if paciente_identificado:
        relato_para_llm = re.sub(re.escape(paciente_identificado), "[PACIENTE]", relato_seguro, flags=re.IGNORECASE)

    resultado_llm = _chamar_gemini_relato(relato_para_llm, catalogo)
    if resultado_llm and isinstance(resultado_llm.get("itens"), list):
        modelo_usado = f"Google Gemini ({settings.GEMINI_MODEL})"
        crm_identificado = resultado_llm.get("crm_identificado") or crm_regras
        itens_brutos = []
        for it in resultado_llm["itens"]:
            if not isinstance(it, dict):
                continue
            prod_obj = mapa_produtos.get(it.get("produto_id"))
            qtd = _numero(it.get("quantidade", 1))
            if not prod_obj or qtd is None or qtd < 1:
                continue
            itens_brutos.append({
                "produto": prod_obj,
                "quantidade": int(qtd),
                "dose_prescrita_mg": _numero(it.get("dose_prescrita_mg")),
            })
    else:
        modelo_usado = "Extrator local por regras (sem GEMINI_API_KEY)"
        crm_identificado = crm_regras
        itens_brutos = _extrair_itens_regras(relato_seguro, produtos_db)

    # o mesmo produto citado duas vezes vira um item só, para a checagem de saldo valer pelo total
    agrupados = {}
    for item in itens_brutos:
        pid = item["produto"].id
        if pid in agrupados:
            agrupados[pid]["quantidade"] += item["quantidade"]
            doses = [d for d in (agrupados[pid]["dose_prescrita_mg"], item["dose_prescrita_mg"]) if d is not None]
            agrupados[pid]["dose_prescrita_mg"] = max(doses) if doses else None
        else:
            agrupados[pid] = dict(item)
    itens_brutos = list(agrupados.values())

    itens_validados: List[estoque_schemas.ItemExtraidoIA] = []
    possui_bloqueio = False

    for item in itens_brutos:
        prod: estoque_models.Produto = item["produto"]
        qtd: int = item["quantidade"]
        dose: Optional[float] = item["dose_prescrita_mg"]

        status_val = "APROVADO"
        msg = f"OK. Saldo atual {prod.saldo_atual}, baixa de {qtd} un."

        if prod.dose_maxima is not None and dose is not None and dose > prod.dose_maxima:
            status_val = "BLOQUEADO_DOSE_LETAL"
            possui_bloqueio = True
            msg = f"Dose de {dose} mg acima da máxima cadastrada ({prod.dose_maxima} mg) para {prod.nome}."
        elif prod.dose_maxima is not None and dose is None:
            status_val = "BLOQUEADO_SEM_DOSE"
            possui_bloqueio = True
            msg = f"O relato não informa a dose de {prod.nome}, que tem dose máxima cadastrada."
        elif prod.controlado and not crm_identificado:
            status_val = "BLOQUEADO_SEM_CRM"
            possui_bloqueio = True
            msg = f"{prod.nome} é controlado (Portaria 344/98) e o relato não traz CRM."
        elif qtd > prod.saldo_atual:
            status_val = "BLOQUEADO_SEM_SALDO"
            possui_bloqueio = True
            msg = f"Pedido de {qtd} un. de {prod.nome}, mas o saldo é {prod.saldo_atual}."

        itens_validados.append(
            estoque_schemas.ItemExtraidoIA(
                produto_id=prod.id,
                produto_nome=prod.nome,
                quantidade=qtd,
                dose_prescrita_mg=dose,
                controlado=bool(prod.controlado),
                dose_maxima_permitida_mg=prod.dose_maxima,
                status_validacao=status_val,
                mensagem_seguranca=msg,
            )
        )

    baixas_realizadas = 0
    mov_ids: List[int] = []

    if not itens_validados:
        status_geral = "REVISAO_NECESSARIA"
        resumo_ia = (
            "Nenhum item do catálogo foi encontrado no relato. "
            "Confira a grafia ou cadastre o item antes."
        )
    elif possui_bloqueio:
        status_geral = "BLOQUEADO_PELA_TRAVA_HOSPITALAR"
        resumo_ia = (
            "Itens encontrados, mas pelo menos um foi barrado por uma trava (dose, CRM ou saldo). "
            "Nenhuma baixa foi feita."
        )
    else:
        status_geral = "APROVADO"
        if request.executar_baixa_automatica:
            for item_val in itens_validados:
                mov_schema = estoque_schemas.MovimentacaoCreate(
                    produto_id=item_val.produto_id,
                    tipo="saida",
                    quantidade=item_val.quantidade,
                    crm_medico=crm_identificado,
                    dose_prescrita=item_val.dose_prescrita_mg,
                    nome_paciente=paciente_identificado or "Paciente Cirúrgico",
                    observacao="Baixa automatizada via leitura de relato cirúrgico",
                )
                nova_mov = estoque_service.create_movimentacao(db, mov_schema)
                baixas_realizadas += 1
                mov_ids.append(nova_mov.id)
            resumo_ia = f"Todas as travas passaram. {baixas_realizadas} baixa(s) registrada(s) no estoque."
        else:
            resumo_ia = (
                f"{len(itens_validados)} item(ns) aprovado(s) nas travas. "
                f"Nada foi baixado: marque a baixa automática para registrar."
            )

    auditoria = estoque_models.HistoricoIA(
        tipo_analise="relato_cirurgico",
        entrada_usuario=relato_seguro,
        resposta_resumo=resumo_ia,
        modelo_utilizado=modelo_usado,
        status_seguranca=status_geral,
    )
    db.add(auditoria)
    db.commit()

    return estoque_schemas.RelatoCirurgicoResponse(
        modelo_utilizado=modelo_usado,
        paciente_identificado=paciente_identificado,
        crm_identificado=crm_identificado,
        status_geral=status_geral,
        resumo_clinico_ia=resumo_ia,
        itens_identificados=itens_validados,
        baixas_realizadas=baixas_realizadas,
        movimentacoes_geradas_ids=mov_ids,
    )


def gerar_relatorio_inteligente_estoque(db: Session) -> estoque_schemas.RelatorioInteligenteResponse:
    resumo_db = estoque_service.get_dashboard_resumo(db)
    alertas = resumo_db.alertas_emergencia
    kpis = resumo_db.kpis

    dados_contexto = {
        "total_produtos": kpis.total_produtos,
        "itens_em_alerta_critico": kpis.itens_em_alerta_critico,
        "produtos_controlados": kpis.produtos_controlados,
        "valor_total_estoque_reais": kpis.valor_total_estoque,
        "insumos_criticos": [
            {
                "nome": p.nome,
                "saldo_atual": p.saldo_atual,
                "minimo_emergencia": p.estoque_minimo_emergencia,
                "deficit": max(0, p.estoque_minimo_emergencia - p.saldo_atual),
                "preco_unitario": p.preco,
            }
            for p in alertas
        ],
    }

    if kpis.itens_em_alerta_critico >= 2:
        nivel_risco = "CRITICO"
    elif kpis.itens_em_alerta_critico == 1:
        nivel_risco = "MODERADO"
    else:
        nivel_risco = "BAIXO"

    modelo_usado = "Cálculo local (sem GEMINI_API_KEY)"
    diagnostico = None
    recomendacoes: List[str] = []
    analise_anvisa = None

    prompt = f"""
Você é farmacêutico responsável por um centro cirúrgico.
Com os indicadores abaixo, escreva um parecer curto em JSON:
{json.dumps(dados_contexto, ensure_ascii=False)}

Retorne só JSON com as chaves:
- "diagnostico_executivo": texto sobre o risco de faltar insumo para cirurgias
- "recomendacoes_compras": lista de textos com quantidade sugerida e custo estimado
- "analise_seguranca_anvisa": texto sobre os medicamentos controlados (Portaria 344/98)
"""
    parsed = _chamar_gemini(prompt, 0.2)
    if parsed and parsed.get("diagnostico_executivo"):
        diagnostico = str(parsed.get("diagnostico_executivo"))
        recomendacoes = [str(r) for r in parsed.get("recomendacoes_compras", []) if r]
        analise_anvisa = str(parsed.get("analise_seguranca_anvisa") or "")
        modelo_usado = f"Google Gemini ({settings.GEMINI_MODEL})"

    if not diagnostico:
        if alertas:
            nomes_criticos = ", ".join(
                [f"{p.nome} (Saldo: {p.saldo_atual} / Mín: {p.estoque_minimo_emergencia})" for p in alertas]
            )
            diagnostico = (
                f"Risco {nivel_risco}: {len(alertas)} insumo(s) no mínimo ou abaixo: {nomes_criticos}. "
                f"Sem reposição, há chance de cirurgia ser suspensa."
            )
            for p in alertas:
                qtd_repor = max(10, (p.estoque_minimo_emergencia * 2) - p.saldo_atual)
                custo_est = round(qtd_repor * p.preco, 2)
                recomendacoes.append(f"Repor {qtd_repor} un. de {p.nome} (custo estimado R$ {custo_est:.2f}).")
        else:
            diagnostico = "Risco BAIXO: todos os insumos estão acima do estoque mínimo."
            recomendacoes.append("Nenhuma compra emergencial; manter o ciclo normal de compras.")

        analise_anvisa = (
            f"{kpis.produtos_controlados} medicamento(s) controlado(s) pela Portaria 344/98. "
            f"Saídas desses itens só são aceitas com CRM informado."
        )

    auditoria = estoque_models.HistoricoIA(
        tipo_analise="relatorio_estoque",
        entrada_usuario="Parecer de estoque solicitado pelo usuário",
        resposta_resumo=diagnostico,
        modelo_utilizado=modelo_usado,
        status_seguranca=f"RISCO_{nivel_risco}",
    )
    db.add(auditoria)
    db.commit()

    return estoque_schemas.RelatorioInteligenteResponse(
        modelo_utilizado=modelo_usado,
        gerado_em=datetime.now(timezone.utc).replace(tzinfo=None),
        nivel_risco_hospitalar=nivel_risco,
        diagnostico_executivo=diagnostico,
        recomendacoes_compras=recomendacoes,
        analise_seguranca_anvisa=analise_anvisa,
        dados_analisados=dados_contexto,
    )


def listar_historico_ia(db: Session, limit: int = 20) -> List[estoque_models.HistoricoIA]:
    return (
        db.query(estoque_models.HistoricoIA)
        .order_by(estoque_models.HistoricoIA.data_hora.desc(), estoque_models.HistoricoIA.id.desc())
        .limit(limit)
        .all()
    )
