from fastapi import APIRouter
from app.api.v1.endpoints import categorias, produtos, movimentacoes, dashboard, ia

api_router = APIRouter()
api_router.include_router(categorias.router, prefix="/categorias", tags=["categorias"])
api_router.include_router(produtos.router, prefix="/produtos", tags=["produtos"])
api_router.include_router(movimentacoes.router, prefix="/movimentacoes", tags=["movimentacoes"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard e fornecedores"])
api_router.include_router(ia.router, prefix="/ia", tags=["ia"])
