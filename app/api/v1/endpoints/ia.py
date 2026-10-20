from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from app.core.config import settings
from app.core.database import get_db
from app.schemas import estoque_schemas
from app.services import ia_service

router = APIRouter()


class ChaveGeminiRequest(BaseModel):
    api_key: str


@router.get("/status-chave", summary="Verificar se a chave da API Google Gemini está ativa")
def status_chave_gemini():
    ativa = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    return {
        "gemini_api_ativa": ativa,
        "modelo_configurado": settings.GEMINI_MODEL if ativa else "Motor Clínico NLP Local (Sem chave externa)",
    }


@router.post("/configurar-chave", summary="Definir chave da API Google Gemini em tempo de execução")
def configurar_chave_gemini(payload: ChaveGeminiRequest):
    settings.GEMINI_API_KEY = payload.api_key.strip()
    ativa = bool(settings.GEMINI_API_KEY)
    return {
        "gemini_api_ativa": ativa,
        "mensagem": (
            f"Chave Google Gemini ({settings.GEMINI_MODEL}) ativada com sucesso!"
            if ativa
            else "Chave removida. Utilizando Motor Clínico NLP Local."
        ),
    }


@router.post(
    "/interpretar-relato",
    response_model=estoque_schemas.RelatoCirurgicoResponse,
    summary="Assistente Cirúrgico IA: Interpreta relato médico em linguagem natural e valida travas hospitalares",
)
def interpretar_relato_cirurgico_endpoint(
    request: estoque_schemas.RelatoCirurgicoRequest,
    db: Session = Depends(get_db),
):
    return ia_service.interpretar_relato_cirurgico(db, request)


@router.post(
    "/relatorio-inteligente",
    response_model=estoque_schemas.RelatorioInteligenteResponse,
    summary="Consultor Farmacêutico IA: Gera parecer executivo de risco cirúrgico e recomendações de compra",
)
def gerar_relatorio_inteligente_endpoint(db: Session = Depends(get_db)):
    return ia_service.gerar_relatorio_inteligente_estoque(db)


@router.get(
    "/historico",
    response_model=List[estoque_schemas.HistoricoIASchema],
    summary="Listar histórico de auditoria das análises realizadas pela IA",
)
def listar_historico_ia_endpoint(db: Session = Depends(get_db)):
    return ia_service.listar_historico_ia(db)
