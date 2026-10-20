from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== CATEGORIA ====================
class CategoriaBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome único da categoria hospitalar")
    descricao: Optional[str] = Field(default=None, max_length=255)


class CategoriaCreate(CategoriaBase):
    pass


class Categoria(CategoriaBase):
    id: int

    model_config = {"from_attributes": True}


class CategoriaUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descricao: Optional[str] = Field(default=None, max_length=255)


# ==================== FORNECEDOR (Normalização CP2) ====================
class FornecedorBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    cnpj: Optional[str] = Field(default=None, max_length=20)
    contato_emergencia: Optional[str] = Field(default=None, max_length=100)


class FornecedorCreate(FornecedorBase):
    pass


class Fornecedor(FornecedorBase):
    id: int

    model_config = {"from_attributes": True}


# ==================== PRODUTO ====================
class ProdutoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    preco: float = Field(..., gt=0, description="Preço unitário do insumo em R$")
    categoria_id: int
    fornecedor_id: Optional[int] = None
    lote: Optional[str] = "LOTE-2026A"
    unidade_medida: str = "ampola"
    controlado: bool = False
    dose_maxima: Optional[float] = Field(default=None, gt=0, description="Dose máxima segura em mg")
    estoque_minimo_emergencia: int = Field(default=0, ge=0)


class ProdutoCreate(ProdutoBase):
    saldo_inicial: int = Field(default=0, ge=0, description="Saldo inicial opcional ao cadastrar")


class Produto(ProdutoBase):
    id: int
    saldo_atual: int

    model_config = {"from_attributes": True}


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=150)
    preco: Optional[float] = Field(default=None, gt=0)
    categoria_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    lote: Optional[str] = None
    unidade_medida: Optional[str] = None
    controlado: Optional[bool] = None
    dose_maxima: Optional[float] = Field(default=None, gt=0)
    estoque_minimo_emergencia: Optional[int] = Field(default=None, ge=0)


# ==================== MOVIMENTACAO ====================
class MovimentacaoBase(BaseModel):
    produto_id: int
    tipo: str = Field(..., pattern="^(entrada|saida)$")
    quantidade: int = Field(..., gt=0)
    crm_medico: Optional[str] = None
    dose_prescrita: Optional[float] = Field(default=None, gt=0)
    nome_paciente: Optional[str] = None
    observacao: Optional[str] = None


class MovimentacaoCreate(MovimentacaoBase):
    pass


class Movimentacao(MovimentacaoBase):
    id: int
    data_hora: datetime

    model_config = {"from_attributes": True}


# ==================== DASHBOARD ====================
class DashboardKPIs(BaseModel):
    total_produtos: int
    total_categorias: int
    itens_em_alerta_critico: int
    produtos_controlados: int
    valor_total_estoque: float
    total_movimentacoes: int
    total_entradas: int
    total_saidas: int


class CategoriaDistribuicao(BaseModel):
    categoria: str
    quantidade_produtos: int
    unidades_estoque: int
    valor_financeiro: float


class EstoqueComparativoItem(BaseModel):
    id: int
    nome: str
    saldo_atual: int
    estoque_minimo_emergencia: int
    em_alerta: bool
    controlado: bool


class MovimentacaoDetalhada(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    tipo: str
    quantidade: int
    crm_medico: Optional[str] = None
    dose_prescrita: Optional[float] = None
    nome_paciente: Optional[str] = None
    observacao: Optional[str] = None
    data_hora: datetime


class DashboardResumo(BaseModel):
    kpis: DashboardKPIs
    alertas_emergencia: List[Produto]
    distribuicao_categorias: List[CategoriaDistribuicao]
    estoque_comparativo: List[EstoqueComparativoItem]
    ultimas_movimentacoes: List[MovimentacaoDetalhada]


# ==================== INTELIGÊNCIA ARTIFICIAL (LLM) ====================
class RelatoCirurgicoRequest(BaseModel):
    relato_texto: str = Field(
        ...,
        min_length=10,
        description="Relato em linguagem natural da equipe médica/enfermagem sobre os insumos utilizados no procedimento."
    )
    executar_baixa_automatica: bool = Field(
        default=False,
        description="Se True e todas as travas de segurança (ANVISA, Dose Segura e Saldo) passarem, registra a saída no banco automaticamente."
    )


class ItemExtraidoIA(BaseModel):
    produto_id: Optional[int] = None
    produto_nome: str
    quantidade: int
    dose_prescrita_mg: Optional[float] = None
    controlado: bool = False
    dose_maxima_permitida_mg: Optional[float] = None
    status_validacao: str  # 'APROVADO', 'BLOQUEADO_DOSE_LETAL', 'BLOQUEADO_SEM_CRM', 'BLOQUEADO_SEM_SALDO', 'NAO_ENCONTRADO'
    mensagem_seguranca: str


class RelatoCirurgicoResponse(BaseModel):
    modelo_utilizado: str
    paciente_identificado: Optional[str] = None
    crm_identificado: Optional[str] = None
    status_geral: str  # 'APROVADO', 'BLOQUEADO_PELA_TRAVA_HOSPITALAR', 'REVISAO_NECESSARIA'
    resumo_clinico_ia: str
    itens_identificados: List[ItemExtraidoIA]
    baixas_realizadas: int = 0
    movimentacoes_geradas_ids: List[int] = []


class RelatorioInteligenteResponse(BaseModel):
    modelo_utilizado: str
    gerado_em: datetime
    nivel_risco_hospitalar: str  # 'BAIXO', 'MODERADO', 'CRITICO'
    diagnostico_executivo: str
    recomendacoes_compras: List[str]
    analise_seguranca_anvisa: str
    dados_analisados: dict


class HistoricoIASchema(BaseModel):
    id: int
    tipo_analise: str
    entrada_usuario: str
    resposta_resumo: str
    modelo_utilizado: str
    status_seguranca: str
    data_hora: datetime

    model_config = {"from_attributes": True}
