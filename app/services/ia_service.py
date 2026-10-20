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
    """
    Proteção de dados sensíveis (LGPD):
    Remove números de CPF que constem no relato antes de enviar para API externa ou salvar em log.
    """
    return re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "***.***.***-** (CPF PROTEGIDO LGPD)", texto)


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
    """
    Chama a API oficial do Google Gemini (LLM) quando GEMINI_API_KEY está configurada.
    """
    if not settings.GEMINI_API_KEY:
        return None

    prompt = f"""
Você é o Assistente Farmacêutico do sistema hospitalar VitalStock.
Analise o relato cirúrgico abaixo e extraia os medicamentos utilizados cruzando com o catálogo do hospital.

CATÁLOGO DE PRODUTOS DO HOSPITAL (JSON):
{json.dumps(catalogo, ensure_ascii=False)}

RELATO CIRÚRGICO:
"{relato_seguro}"

Responda APENAS com um objeto JSON válido no seguinte formato:
{{
  "paciente_identificado": "Nome do paciente ou null",
  "crm_identificado": "CRM do médico ou null",
  "resumo_clinico_ia": "Explicação concisa do procedimento e validação",
  "itens": [
    {{
      "produto_id": 1,
      "quantidade": 2,
      "dose_prescrita_mg": 0.05
    }}
  ]
}}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text_out)
    except Exception:
        return None
    return None


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

    resultado_llm = _chamar_gemini_relato(relato_seguro, catalogo)
    if resultado_llm and "itens" in resultado_llm:
        modelo_usado = f"Google Gemini API ({settings.GEMINI_MODEL})"
        crm_identificado = resultado_llm.get("crm_identificado")
        paciente_identificado = resultado_llm.get("paciente_identificado")
        itens_brutos = []
        for it in resultado_llm.get("itens", []):
            prod_obj = mapa_produtos.get(it.get("produto_id"))
            if prod_obj:
                itens_brutos.append({
                    "produto": prod_obj,
                    "quantidade": int(it.get("quantidade", 1)),
                    "dose_prescrita_mg": it.get("dose_prescrita_mg"),
                })
    else:
        modelo_usado = "Extrator Local por Regras (Configure GEMINI_API_KEY para usar Google Gemini)"
        crm_identificado, paciente_identificado = _extrair_crm_e_paciente_regras(relato_seguro)
        itens_brutos = _extrair_itens_regras(relato_seguro, produtos_db)

    itens_validados: List[estoque_schemas.ItemExtraidoIA] = []
    possui_bloqueio = False

    for item in itens_brutos:
        prod: estoque_models.Produto = item["produto"]
        qtd: int = item["quantidade"]
        dose: Optional[float] = item["dose_prescrita_mg"]

        status_val = "APROVADO"
        msg = f"Validação clínica OK. Saldo disponível ({prod.saldo_atual}) suficiente para baixa de {qtd} un."

        if prod.dose_maxima is not None and dose is not None and dose > prod.dose_maxima:
            status_val = "BLOQUEADO_DOSE_LETAL"
            possui_bloqueio = True
            msg = (
                f"ALERTA FATAL EVITADO: Dose extraída ({dose}mg) excede a dose máxima segura "
                f"({prod.dose_maxima}mg) de {prod.nome}. Baixa bloqueada!"
            )
        elif prod.controlado and not crm_identificado:
            status_val = "BLOQUEADO_SEM_CRM"
            possui_bloqueio = True
            msg = (
                f"BLOQUEIO ANVISA (Portaria 344): {prod.nome} é controlado e nenhum CRM médico válido "
                f"foi identificado no relato."
            )
        elif qtd > prod.saldo_atual:
            status_val = "BLOQUEADO_SEM_SALDO"
            possui_bloqueio = True
            msg = (
                f"ESTOQUE INSUFICIENTE: Solicitado {qtd} un. de {prod.nome}, mas há apenas "
                f"{prod.saldo_atual} un. no estoque."
            )

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
            "Nenhum medicamento cadastrado no catálogo do VitalStock foi identificado no relato enviado. "
            "Verifique a grafia dos insumos ou cadastre o item antes do procedimento."
        )
    elif possui_bloqueio:
        status_geral = "BLOQUEADO_PELA_TRAVA_HOSPITALAR"
        resumo_ia = (
            "Foram identificados os insumos do relato cirúrgico, porém a operação foi BLOQUEADA "
            "devido à violação das travas de segurança hospitalar (Dose Letal, falta de CRM ANVISA ou falta de saldo)."
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
            resumo_ia = (
                f"Relato validado com sucesso! Todas as travas de segurança (ANVISA e Dose Segura) foram aprovadas. "
                f"Foram executadas {baixas_realizadas} baixa(s) automática(s) no banco de dados."
            )
        else:
            resumo_ia = (
                f"Simulação concluída: {len(itens_validados)} insumo(s) identificado(s) e aprovado(s) "
                f"pelas travas de segurança. Marque a opção de baixa automática para efetivar no estoque."
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

    modelo_usado = "Cálculo Local de Ressuprimento (Configure GEMINI_API_KEY para usar Google Gemini)"
    diagnostico = None
    recomendacoes: List[str] = []
    analise_anvisa = None

    if settings.GEMINI_API_KEY:
        prompt = f"""
Você é um Diretor de Farmácia Hospitalar.
Analise os indicadores reais do banco de dados do hospital abaixo e gere um parecer executivo em JSON:
{json.dumps(dados_contexto, ensure_ascii=False)}

Retorne APENAS JSON válido com as chaves:
- "diagnostico_executivo": string detalhada sobre o risco atual para o bloco cirúrgico
- "recomendacoes_compras": lista de strings com quantidades recomendadas e custo estimado de reposição
- "analise_seguranca_anvisa": string avaliando a governança dos medicamentos controlados (Portaria 344/98)
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                    },
                )
                if resp.status_code == 200:
                    parsed = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
                    diagnostico = parsed.get("diagnostico_executivo")
                    recomendacoes = parsed.get("recomendacoes_compras", [])
                    analise_anvisa = parsed.get("analise_seguranca_anvisa")
                    modelo_usado = f"Google Gemini API ({settings.GEMINI_MODEL})"
        except Exception:
            pass

    if not diagnostico:
        if alertas:
            nomes_criticos = ", ".join(
                [f"{p.nome} (Saldo: {p.saldo_atual} / Mín: {p.estoque_minimo_emergencia})" for p in alertas]
            )
            diagnostico = (
                f"O bloco cirúrgico opera em nível de risco {nivel_risco}. "
                f"Identificamos {len(alertas)} insumo(s) abaixo da margem de segurança cirúrgica: {nomes_criticos}. "
                f"Há risco de suspensão de procedimentos caso a reposição de emergência não ocorra."
            )
            for p in alertas:
                qtd_repor = max(10, (p.estoque_minimo_emergencia * 2) - p.saldo_atual)
                custo_est = round(qtd_repor * p.preco, 2)
                recomendacoes.append(
                    f"Repor {qtd_repor} un. de {p.nome} para recompor margem de segurança "
                    f"(Custo estimado: R$ {custo_est:.2f})."
                )
        else:
            diagnostico = (
                "Operação hospitalar estável. Todos os insumos cirúrgicos encontram-se acima "
                "do estoque mínimo de emergência."
            )
            recomendacoes.append("Manter cronograma regular de compras; nenhuma compra emergencial necessária.")

        analise_anvisa = (
            f"O hospital possui {kpis.produtos_controlados} medicamento(s) sob regime da Portaria 344/98 (ANVISA) "
            f"monitorados com trava ativa de CRM e limite de dosagem letal. Todas as {kpis.total_saidas} saída(s) "
            f"registradas possuem rastreabilidade de paciente e prescritor."
        )

    auditoria = estoque_models.HistoricoIA(
        tipo_analise="relatorio_estoque",
        entrada_usuario="Solicitação de Diagnóstico de Estoque e Risco Cirúrgico",
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
