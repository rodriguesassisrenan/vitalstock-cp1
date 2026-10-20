import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.services import estoque_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
        "API de estoque da farmácia hospitalar: cadastro de insumos, entradas e saídas com "
        "travas de CRM (Portaria 344/98), dose máxima e saldo, dashboard e leitura de relatos "
        "cirúrgicos com o Gemini."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "A operação viola uma restrição do banco (registro duplicado ou referência inexistente)."},
    )

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health", tags=["monitoramento"], summary="Healthcheck usado pelo Docker")
def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "llm": settings.GEMINI_MODEL if settings.GEMINI_API_KEY else "desativado (sem GEMINI_API_KEY)",
    }
