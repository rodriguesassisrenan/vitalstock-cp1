from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import estoque_service

router = APIRouter()


@router.get("/", response_model=List[estoque_schemas.Produto], summary="Listar produtos com filtros e paginação")
def read_produtos(
    skip: int = Query(0, ge=0, description="Registros para pular (paginação)"),
    limit: int = Query(100, ge=1, le=500, description="Limite de registros por página"),
    categoria_id: Optional[int] = Query(None, description="Filtrar por ID da categoria"),
    controlado: Optional[bool] = Query(None, description="Filtrar por medicamentos controlados (ANVISA)"),
    apenas_alerta: Optional[bool] = Query(False, description="Retornar apenas produtos abaixo do estoque mínimo"),
    busca: Optional[str] = Query(None, description="Busca textual pelo nome do medicamento/insumo"),
    db: Session = Depends(get_db),
):
    return estoque_service.get_produtos(
        db,
        skip=skip,
        limit=limit,
        categoria_id=categoria_id,
        controlado=controlado,
        apenas_alerta=apenas_alerta,
        busca=busca,
    )


@router.get(
    "/alertas-emergencia",
    response_model=List[estoque_schemas.Produto],
    summary="Listar insumos com saldo no mínimo ou abaixo",
)
def get_alertas_estoque_emergencia(db: Session = Depends(get_db)):
    return estoque_service.get_produtos_em_alerta(db)


@router.get("/{produto_id}", response_model=estoque_schemas.Produto, summary="Buscar produto por ID")
def read_produto(produto_id: int, db: Session = Depends(get_db)):
    return estoque_service.get_produto(db, produto_id)


@router.post(
    "/",
    response_model=estoque_schemas.Produto,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar medicamento ou insumo",
)
def create_produto(produto: estoque_schemas.ProdutoCreate, db: Session = Depends(get_db)):
    return estoque_service.create_produto(db, produto)


@router.put("/{produto_id}", response_model=estoque_schemas.Produto, summary="Atualizar dados de um produto")
def update_produto(produto_id: int, produto_update: estoque_schemas.ProdutoUpdate, db: Session = Depends(get_db)):
    return estoque_service.update_produto(db, produto_id, produto_update)


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover produto (bloqueado se já tiver movimentações)")
def delete_produto(produto_id: int, db: Session = Depends(get_db)):
    estoque_service.delete_produto(db, produto_id)
