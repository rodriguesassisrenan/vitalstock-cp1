import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.services import estoque_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas normalizadas do banco de dados ao iniciar
    Base.metadata.create_all(bind=engine)
    # Popula dados iniciais hospitalares realistas caso o banco esteja vazio
    if settings.AUTO_SEED:
        db = SessionLocal()
        try:
            estoque_service.seed_initial_data(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "API RESTful, Dashboard Hospitalar e Agente de Inteligência Artificial (LLM) para "
        "controle rígido de insumos cirúrgicos, prevenção de erros médicos (Dose Letal) e "
        "conformidade com a Portaria 344/98 da ANVISA."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve a aplicação Frontend e o Dashboard de Controle Hospitalar"""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health", tags=["monitoramento & deploy"], summary="Healthcheck do container e status do serviço")
def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "llm_integration": "Google Gemini API + Clinical NLP Fallback Ready",
    }
