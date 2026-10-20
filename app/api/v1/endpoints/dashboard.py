from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import estoque_service

router = APIRouter()


@router.get(
    "/resumo",
    response_model=estoque_schemas.DashboardResumo,
    summary="Dados consolidados do dashboard",
)
def read_dashboard_resumo(db: Session = Depends(get_db)):
    """KPIs, alertas, distribuição por categoria e últimas 12 movimentações numa chamada só."""
    return estoque_service.get_dashboard_resumo(db)


@router.get(
    "/fornecedores",
    response_model=List[estoque_schemas.Fornecedor],
    summary="Listar fornecedores",
)
def read_fornecedores(db: Session = Depends(get_db)):
    return estoque_service.get_fornecedores(db)


@router.post(
    "/fornecedores",
    response_model=estoque_schemas.Fornecedor,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar fornecedor",
)
def create_fornecedor(fornecedor: estoque_schemas.FornecedorCreate, db: Session = Depends(get_db)):
    return estoque_service.create_fornecedor(db, fornecedor)
