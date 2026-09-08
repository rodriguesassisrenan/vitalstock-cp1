from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import estoque_models
from app.schemas import estoque_schemas

# Categoria
def get_categorias(db: Session, skip: int = 0, limit: int = 100):
    return db.query(estoque_models.Categoria).offset(skip).limit(limit).all()

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

# Produto
def get_produtos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(estoque_models.Produto).offset(skip).limit(limit).all()

def get_produtos_em_alerta(db: Session):
    # Retorna produtos cujo estoque atual atingiu ou caiu abaixo do limite de segurança cirúrgico
    return db.query(estoque_models.Produto).filter(estoque_models.Produto.saldo_atual <= estoque_models.Produto.estoque_minimo_emergencia).all()

def get_produto(db: Session, produto_id: int):
    produto = db.query(estoque_models.Produto).filter(estoque_models.Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return produto

def create_produto(db: Session, produto: estoque_schemas.ProdutoCreate):
    get_categoria(db, produto.categoria_id) # Verifica se categoria existe
    db_produto = estoque_models.Produto(**produto.model_dump())
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto

def update_produto(db: Session, produto_id: int, produto_update: estoque_schemas.ProdutoUpdate):
    db_produto = get_produto(db, produto_id)
    update_data = produto_update.model_dump(exclude_unset=True)
    
    if "categoria_id" in update_data:
        get_categoria(db, update_data["categoria_id"]) # Verifica se categoria existe
        
    for key, value in update_data.items():
        setattr(db_produto, key, value)
        
    db.commit()
    db.refresh(db_produto)
    return db_produto

def delete_produto(db: Session, produto_id: int):
    produto = get_produto(db, produto_id)
    db.delete(produto)
    db.commit()

# Movimentacao
def get_movimentacoes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(estoque_models.Movimentacao).offset(skip).limit(limit).all()

def create_movimentacao(db: Session, movimentacao: estoque_schemas.MovimentacaoCreate):
    produto = get_produto(db, movimentacao.produto_id) # Verifica se produto existe
    
    if movimentacao.tipo == "saida":
        # 1. Trava da Anvisa
        if produto.controlado and not movimentacao.crm_medico:
            raise HTTPException(
                status_code=400, 
                detail="ALERTA DE SEGURANÇA: A saída de um medicamento controlado exige o CRM do médico solicitante."
            )
            
        # 2. Trava de Dosagem Segura (Anti-Erro Médico)
        if produto.dose_maxima and movimentacao.dose_prescrita:
            if movimentacao.dose_prescrita > produto.dose_maxima:
                raise HTTPException(
                    status_code=400,
                    detail=f"ALERTA FATAL EVITADO: A dose prescrita ({movimentacao.dose_prescrita}) excede o limite MÁXIMO SEGURO permitido ({produto.dose_maxima}) para {produto.nome}. O sistema bloqueou a saída para garantir a vida do paciente."
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
