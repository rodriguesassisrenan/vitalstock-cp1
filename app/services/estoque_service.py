from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from fastapi import HTTPException
from app.models import estoque_models
from app.schemas import estoque_schemas


# --- categoria
def get_categorias(db: Session, skip: int = 0, limit: int = 100):
    return db.query(estoque_models.Categoria).order_by(estoque_models.Categoria.id).offset(skip).limit(limit).all()


def get_categoria(db: Session, categoria_id: int):
    categoria = db.query(estoque_models.Categoria).filter(estoque_models.Categoria.id == categoria_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return categoria


def create_categoria(db: Session, categoria: estoque_schemas.CategoriaCreate):
    db_categoria = db.query(estoque_models.Categoria).filter(estoque_models.Categoria.nome == categoria.nome).first()
    if db_categoria:
        raise HTTPException(status_code=400, detail="Categoria já cadastrada com este nome")

    db_categoria = estoque_models.Categoria(**categoria.model_dump())
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria


def update_categoria(db: Session, categoria_id: int, categoria_update: estoque_schemas.CategoriaUpdate):
    db_categoria = get_categoria(db, categoria_id)
    update_data = categoria_update.model_dump(exclude_unset=True)

    if "nome" in update_data and update_data["nome"] != db_categoria.nome:
        check_nome = db.query(estoque_models.Categoria).filter(estoque_models.Categoria.nome == update_data["nome"]).first()
        if check_nome:
            raise HTTPException(status_code=400, detail="Categoria já cadastrada com este nome")

    for key, value in update_data.items():
        setattr(db_categoria, key, value)

    db.commit()
    db.refresh(db_categoria)
    return db_categoria


def delete_categoria(db: Session, categoria_id: int):
    categoria = get_categoria(db, categoria_id)
    if categoria.produtos:
        raise HTTPException(status_code=400, detail="Não é possível excluir categoria com produtos vinculados")
    db.delete(categoria)
    db.commit()


# --- fornecedor
def get_fornecedores(db: Session, skip: int = 0, limit: int = 100):
    return db.query(estoque_models.Fornecedor).order_by(estoque_models.Fornecedor.id).offset(skip).limit(limit).all()


def get_fornecedor(db: Session, fornecedor_id: int):
    fornecedor = db.query(estoque_models.Fornecedor).filter(estoque_models.Fornecedor.id == fornecedor_id).first()
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return fornecedor


def create_fornecedor(db: Session, fornecedor: estoque_schemas.FornecedorCreate):
    existente = db.query(estoque_models.Fornecedor).filter(estoque_models.Fornecedor.nome == fornecedor.nome).first()
    if existente:
        raise HTTPException(status_code=400, detail="Fornecedor já cadastrado com este nome")
    db_fornecedor = estoque_models.Fornecedor(**fornecedor.model_dump())
    db.add(db_fornecedor)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor


# --- produto
def get_produtos(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    categoria_id: Optional[int] = None,
    controlado: Optional[bool] = None,
    apenas_alerta: Optional[bool] = False,
    busca: Optional[str] = None,
):
    query = db.query(estoque_models.Produto)

    if categoria_id is not None:
        query = query.filter(estoque_models.Produto.categoria_id == categoria_id)
    if controlado is not None:
        query = query.filter(estoque_models.Produto.controlado == (1 if controlado else 0))
    if apenas_alerta:
        query = query.filter(
            estoque_models.Produto.saldo_atual <= estoque_models.Produto.estoque_minimo_emergencia
        )
    if busca:
        query = query.filter(estoque_models.Produto.nome.ilike(f"%{busca.strip()}%"))

    return query.order_by(estoque_models.Produto.id).offset(skip).limit(limit).all()


def get_produtos_em_alerta(db: Session):
    return (
        db.query(estoque_models.Produto)
        .filter(estoque_models.Produto.saldo_atual <= estoque_models.Produto.estoque_minimo_emergencia)
        .order_by(estoque_models.Produto.saldo_atual.asc())
        .all()
    )


def get_produto(db: Session, produto_id: int):
    produto = db.query(estoque_models.Produto).filter(estoque_models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return produto


def create_produto(db: Session, produto: estoque_schemas.ProdutoCreate):
    get_categoria(db, produto.categoria_id)
    if produto.fornecedor_id is not None:
        get_fornecedor(db, produto.fornecedor_id)
    dados = produto.model_dump()
    saldo_inicial = dados.pop("saldo_inicial", 0)
    dados["controlado"] = 1 if dados.get("controlado") else 0

    db_produto = estoque_models.Produto(**dados, saldo_atual=saldo_inicial)
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)

    if saldo_inicial > 0:
        mov_inicial = estoque_models.Movimentacao(
            produto_id=db_produto.id,
            tipo="entrada",
            quantidade=saldo_inicial,
            observacao="Carga inicial de lote no cadastro",
        )
        db.add(mov_inicial)
        db.commit()

    return db_produto


def update_produto(db: Session, produto_id: int, produto_update: estoque_schemas.ProdutoUpdate):
    db_produto = get_produto(db, produto_id)
    update_data = produto_update.model_dump(exclude_unset=True)

    # campos obrigatórios no banco: null no PUT significa "não alterar"
    for campo in ("nome", "preco", "categoria_id", "unidade_medida", "controlado", "estoque_minimo_emergencia"):
        if campo in update_data and update_data[campo] is None:
            update_data.pop(campo)

    if "categoria_id" in update_data:
        get_categoria(db, update_data["categoria_id"])
    if update_data.get("fornecedor_id") is not None:
        get_fornecedor(db, update_data["fornecedor_id"])

    if "controlado" in update_data and update_data["controlado"] is not None:
        update_data["controlado"] = 1 if update_data["controlado"] else 0

    for key, value in update_data.items():
        setattr(db_produto, key, value)

    db.commit()
    db.refresh(db_produto)
    return db_produto


def delete_produto(db: Session, produto_id: int):
    produto = get_produto(db, produto_id)
    # o histórico de saídas é a rastreabilidade exigida para controlados; não pode sumir junto
    if produto.movimentacoes:
        raise HTTPException(
            status_code=409,
            detail="Produto possui movimentações registradas e não pode ser excluído.",
        )
    db.delete(produto)
    db.commit()


# --- movimentacao
def get_movimentacoes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    produto_id: Optional[int] = None,
    tipo: Optional[str] = None,
):
    query = db.query(estoque_models.Movimentacao)
    if produto_id is not None:
        query = query.filter(estoque_models.Movimentacao.produto_id == produto_id)
    if tipo:
        query = query.filter(estoque_models.Movimentacao.tipo == tipo)
    return query.order_by(estoque_models.Movimentacao.data_hora.desc(), estoque_models.Movimentacao.id.desc()).offset(skip).limit(limit).all()


def create_movimentacao(db: Session, movimentacao: estoque_schemas.MovimentacaoCreate):
    produto = get_produto(db, movimentacao.produto_id)

    if movimentacao.tipo == "saida":
        # Portaria 344/98: controlado só sai com CRM do prescritor
        if produto.controlado and (not movimentacao.crm_medico or not movimentacao.crm_medico.strip()):
            raise HTTPException(
                status_code=400,
                detail="Saída de medicamento controlado exige o CRM do médico.",
            )

        if produto.dose_maxima:
            if movimentacao.dose_prescrita is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Informe a dose prescrita (mg): {produto.nome} tem dose máxima cadastrada.",
                )
            if movimentacao.dose_prescrita > produto.dose_maxima:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Dose prescrita ({movimentacao.dose_prescrita} mg) acima da dose máxima "
                        f"cadastrada para {produto.nome} ({produto.dose_maxima} mg). Saída bloqueada."
                    ),
                )

    if movimentacao.tipo == "entrada":
        produto.saldo_atual += movimentacao.quantidade
    elif movimentacao.tipo == "saida":
        if movimentacao.quantidade > produto.saldo_atual:
            raise HTTPException(status_code=400, detail="Saldo insuficiente no estoque do hospital.")
        produto.saldo_atual -= movimentacao.quantidade

    db_movimentacao = estoque_models.Movimentacao(**movimentacao.model_dump())
    db.add(db_movimentacao)
    db.commit()
    db.refresh(db_movimentacao)
    return db_movimentacao


# --- dashboard
def get_dashboard_resumo(db: Session) -> estoque_schemas.DashboardResumo:
    """
    Junta KPIs, alertas, distribuição por categoria e últimas movimentações numa resposta só,
    para o frontend não precisar fazer uma chamada por bloco do dashboard.
    """
    categorias = db.query(estoque_models.Categoria).options(joinedload(estoque_models.Categoria.produtos)).all()
    produtos = db.query(estoque_models.Produto).order_by(estoque_models.Produto.id).all()

    contagem_por_tipo = dict(
        db.query(estoque_models.Movimentacao.tipo, func.count(estoque_models.Movimentacao.id))
        .group_by(estoque_models.Movimentacao.tipo)
        .all()
    )
    total_entradas = contagem_por_tipo.get("entrada", 0)
    total_saidas = contagem_por_tipo.get("saida", 0)

    ultimas = (
        db.query(estoque_models.Movimentacao)
        .options(joinedload(estoque_models.Movimentacao.produto))
        .order_by(estoque_models.Movimentacao.data_hora.desc(), estoque_models.Movimentacao.id.desc())
        .limit(12)
        .all()
    )

    alertas = [p for p in produtos if p.saldo_atual <= p.estoque_minimo_emergencia]
    controlados = [p for p in produtos if p.controlado]
    valor_total = round(sum(p.preco * p.saldo_atual for p in produtos), 2)

    kpis = estoque_schemas.DashboardKPIs(
        total_produtos=len(produtos),
        total_categorias=len(categorias),
        itens_em_alerta_critico=len(alertas),
        produtos_controlados=len(controlados),
        valor_total_estoque=valor_total,
        total_movimentacoes=total_entradas + total_saidas,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
    )

    distribuicao = [
        estoque_schemas.CategoriaDistribuicao(
            categoria=cat.nome,
            quantidade_produtos=len(cat.produtos),
            unidades_estoque=sum(p.saldo_atual for p in cat.produtos),
            valor_financeiro=round(sum(p.preco * p.saldo_atual for p in cat.produtos), 2),
        )
        for cat in categorias
    ]

    comparativo = [
        estoque_schemas.EstoqueComparativoItem(
            id=p.id,
            nome=p.nome,
            saldo_atual=p.saldo_atual,
            estoque_minimo_emergencia=p.estoque_minimo_emergencia,
            em_alerta=(p.saldo_atual <= p.estoque_minimo_emergencia),
            controlado=bool(p.controlado),
        )
        for p in produtos
    ]

    ultimas_mov = [
        estoque_schemas.MovimentacaoDetalhada(
            id=m.id,
            produto_id=m.produto_id,
            produto_nome=m.produto.nome if m.produto else f"Produto #{m.produto_id}",
            tipo=m.tipo,
            quantidade=m.quantidade,
            crm_medico=m.crm_medico,
            dose_prescrita=m.dose_prescrita,
            nome_paciente=m.nome_paciente,
            observacao=m.observacao,
            data_hora=m.data_hora,
        )
        for m in ultimas
    ]

    return estoque_schemas.DashboardResumo(
        kpis=kpis,
        alertas_emergencia=alertas,
        distribuicao_categorias=distribuicao,
        estoque_comparativo=comparativo,
        ultimas_movimentacoes=ultimas_mov,
    )


# --- carga inicial
def seed_initial_data(db: Session):
    """Carga de exemplo para a demonstração; só roda com o banco vazio."""
    if db.query(estoque_models.Categoria).count() > 0:
        return

    forn1 = estoque_models.Fornecedor(
        nome="Cristália Produtos Químicos Farmacêuticos",
        cnpj="44.734.671/0001-51",
        contato_emergencia="0800-701-1918",
    )
    forn2 = estoque_models.Fornecedor(
        nome="Ethicon / Johnson & Johnson Medical",
        cnpj="54.516.661/0001-01",
        contato_emergencia="0800-707-5420",
    )
    db.add_all([forn1, forn2])
    db.flush()

    cat_anestesicos = estoque_models.Categoria(
        nome="Anestésicos e Sedativos",
        descricao="Insumos críticos de indução e manutenção anestésica para centro cirúrgico",
    )
    cat_opioides = estoque_models.Categoria(
        nome="Analgésicos Opióides (Portaria 344)",
        descricao="Medicamentos de controle especial ANVISA com alto risco de depressão respiratória",
    )
    cat_antibioticos = estoque_models.Categoria(
        nome="Antibióticos Hospitalares",
        descricao="Antimicrobianos de amplo espectro para profilaxia cirúrgica e UTI",
    )
    cat_suturas = estoque_models.Categoria(
        nome="Fios de Sutura e Descartáveis",
        descricao="Materiais de síntese cirúrgica e hemostasia de bloco operatório",
    )
    cat_analgesicos = estoque_models.Categoria(
        nome="Analgésicos e Antitérmicos",
        descricao="Analgesia não opioide de uso no pós-operatório",
    )
    db.add_all([cat_anestesicos, cat_opioides, cat_antibioticos, cat_suturas, cat_analgesicos])
    db.flush()

    produtos_seed = [
        estoque_models.Produto(
            nome="Fentanil Citrato Injetável 0,05mg/ml",
            preco=42.90,
            categoria_id=cat_opioides.id,
            fornecedor_id=forn1.id,
            lote="FTN-2026-09",
            unidade_medida="ampola 10ml",
            saldo_atual=8,  # abaixo do mínimo (15)
            controlado=1,
            dose_maxima=0.1,
            estoque_minimo_emergencia=15,
        ),
        estoque_models.Produto(
            nome="Propofol Emulsão Injetável 10mg/ml",
            preco=68.50,
            categoria_id=cat_anestesicos.id,
            fornecedor_id=forn1.id,
            lote="PRP-2026-11",
            unidade_medida="frasco-ampola 20ml",
            saldo_atual=35,
            controlado=1,
            dose_maxima=200.0,
            estoque_minimo_emergencia=20,
        ),
        estoque_models.Produto(
            nome="Sulfato de Morfina 10mg/ml",
            preco=29.80,
            categoria_id=cat_opioides.id,
            fornecedor_id=forn1.id,
            lote="MRF-2026-04",
            unidade_medida="ampola 1ml",
            saldo_atual=25,
            controlado=1,
            dose_maxima=15.0,
            estoque_minimo_emergencia=12,
        ),
        estoque_models.Produto(
            nome="Ceftriaxona Dissódica IV 1g",
            preco=18.40,
            categoria_id=cat_antibioticos.id,
            fornecedor_id=forn1.id,
            lote="CEF-2026-08",
            unidade_medida="frasco-ampola",
            saldo_atual=60,
            controlado=0,
            dose_maxima=2000.0,
            estoque_minimo_emergencia=25,
        ),
        estoque_models.Produto(
            nome="Fio de Sutura Nylon 3-0 Agulhado",
            preco=14.20,
            categoria_id=cat_suturas.id,
            fornecedor_id=forn2.id,
            lote="ETH-2026-02",
            unidade_medida="envelope",
            saldo_atual=10,  # abaixo do mínimo (30)
            controlado=0,
            dose_maxima=None,
            estoque_minimo_emergencia=30,
        ),
        estoque_models.Produto(
            nome="Dipirona Sódica Injetável 500mg/ml",
            preco=6.50,
            categoria_id=cat_analgesicos.id,
            fornecedor_id=forn1.id,
            lote="DIP-2026-10",
            unidade_medida="ampola 2ml",
            saldo_atual=90,
            controlado=0,
            dose_maxima=1000.0,
            estoque_minimo_emergencia=40,
        ),
    ]
    db.add_all(produtos_seed)
    db.flush()

    movs_seed = [
        estoque_models.Movimentacao(
            produto_id=produtos_seed[0].id,
            tipo="entrada",
            quantidade=12,
            observacao="Recebimento NF-8821 Farmácia Central",
        ),
        estoque_models.Movimentacao(
            produto_id=produtos_seed[0].id,
            tipo="saida",
            quantidade=4,
            crm_medico="CRM-SP 145890",
            dose_prescrita=0.05,
            nome_paciente="Maria Aparecida Souza (Sala Cirúrgica 02)",
            observacao="Indução anestésica cirurgia oncológica",
        ),
        estoque_models.Movimentacao(
            produto_id=produtos_seed[1].id,
            tipo="saida",
            quantidade=3,
            crm_medico="CRM-SP 145890",
            dose_prescrita=150.0,
            nome_paciente="Maria Aparecida Souza (Sala Cirúrgica 02)",
            observacao="Manutenção anestésica venosa total",
        ),
        estoque_models.Movimentacao(
            produto_id=produtos_seed[4].id,
            tipo="saida",
            quantidade=6,
            crm_medico="CRM-SP 198221",
            dose_prescrita=None,
            nome_paciente="Roberto Carlos Mendes (Bloco Ortopédico)",
            observacao="Síntese cirúrgica pós-artroplastia",
        ),
    ]
    db.add_all(movs_seed)
    db.commit()
