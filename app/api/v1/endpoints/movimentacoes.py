from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import estoque_service

router = APIRouter()

@router.get("/", response_model=List[estoque_schemas.Movimentacao])
def read_movimentacoes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return estoque_service.get_movimentacoes(db, skip=skip, limit=limit)

@router.post("/", response_model=estoque_schemas.Movimentacao, status_code=status.HTTP_201_CREATED)
def create_movimentacao(movimentacao: estoque_schemas.MovimentacaoCreate, db: Session = Depends(get_db)):
    return estoque_service.create_movimentacao(db, movimentacao)
