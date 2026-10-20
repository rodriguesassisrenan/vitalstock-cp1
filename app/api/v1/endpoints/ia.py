from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.config import settings
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import ia_service

router = APIRouter()


@router.get("/status-chave", summary="Informa se a chave do Gemini está configurada no servidor")
def status_chave_gemini():
    ativa = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    return {
        "gemini_api_ativa": ativa,
        "modelo_configurado": settings.GEMINI_MODEL if ativa else "Extrator local por regras (sem LLM)",
    }


@router.post(
    "/interpretar-relato",
    response_model=estoque_schemas.RelatoCirurgicoResponse,
    summary="Lê um relato cirúrgico em texto livre, extrai os insumos e aplica as travas",
)
def interpretar_relato_cirurgico_endpoint(
    request: estoque_schemas.RelatoCirurgicoRequest,
    db: Session = Depends(get_db),
):
    return ia_service.interpretar_relato_cirurgico(db, request)


@router.post(
    "/relatorio-inteligente",
    response_model=estoque_schemas.RelatorioInteligenteResponse,
    summary="Gera parecer de risco de falta de insumos e sugestões de compra",
)
def gerar_relatorio_inteligente_endpoint(db: Session = Depends(get_db)):
    return ia_service.gerar_relatorio_inteligente_estoque(db)


@router.get(
    "/historico",
    response_model=List[estoque_schemas.HistoricoIASchema],
    summary="Lista as últimas análises feitas pela IA",
)
def listar_historico_ia_endpoint(db: Session = Depends(get_db)):
    return ia_service.listar_historico_ia(db)
