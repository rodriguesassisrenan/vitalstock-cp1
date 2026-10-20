from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import estoque_service

router = APIRouter()


@router.get(
    "/",
    response_model=List[estoque_schemas.Movimentacao],
    summary="Listar histórico de movimentações com filtros",
)
def read_movimentacoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    produto_id: Optional[int] = Query(None, description="Filtrar movimentações de um produto específico"),
    tipo: Optional[str] = Query(None, pattern="^(entrada|saida)$", description="Filtrar por entrada ou saida"),
    db: Session = Depends(get_db),
):
    return estoque_service.get_movimentacoes(db, skip=skip, limit=limit, produto_id=produto_id, tipo=tipo)


@router.post(
    "/",
    response_model=estoque_schemas.Movimentacao,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar entrada ou saída de estoque (com Travas ANVISA e Anti-Overdose)",
)
def create_movimentacao(movimentacao: estoque_schemas.MovimentacaoCreate, db: Session = Depends(get_db)):
    return estoque_service.create_movimentacao(db, movimentacao)
