from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import estoque_service

router = APIRouter()

@router.get("/", response_model=List[estoque_schemas.Produto])
def read_produtos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return estoque_service.get_produtos(db, skip=skip, limit=limit)

@router.get("/alertas-emergencia", response_model=List[estoque_schemas.Produto])
def get_alertas_estoque_emergencia(db: Session = Depends(get_db)):
    """Retorna apenas os insumos críticos que estão no limite de causar suspensão de cirurgias"""
    return estoque_service.get_produtos_em_alerta(db)

@router.get("/{produto_id}", response_model=estoque_schemas.Produto)
def read_produto(produto_id: int, db: Session = Depends(get_db)):
    return estoque_service.get_produto(db, produto_id)

@router.post("/", response_model=estoque_schemas.Produto, status_code=status.HTTP_201_CREATED)
def create_produto(produto: estoque_schemas.ProdutoCreate, db: Session = Depends(get_db)):
    return estoque_service.create_produto(db, produto)

@router.put("/{produto_id}", response_model=estoque_schemas.Produto)
def update_produto(produto_id: int, produto_update: estoque_schemas.ProdutoUpdate, db: Session = Depends(get_db)):
    return estoque_service.update_produto(db, produto_id, produto_update)

@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_produto(produto_id: int, db: Session = Depends(get_db)):
    estoque_service.delete_produto(db, produto_id)
