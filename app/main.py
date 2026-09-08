from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas do banco de dados ao iniciar, se não existirem
    Base.metadata.create_all(bind=engine)
    yield
    # Lógica de shutdown pode ir aqui

app = FastAPI(
    title="VitalStock API - Gestão Hospitalar",
    description="API de controle rígido de insumos cirúrgicos e medicamentos controlados.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")
