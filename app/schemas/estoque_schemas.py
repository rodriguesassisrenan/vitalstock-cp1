from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CategoriaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None

class CategoriaCreate(CategoriaBase):
    pass

class Categoria(CategoriaBase):
    id: int

    model_config = {"from_attributes": True}

class CategoriaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None

class ProdutoBase(BaseModel):
    nome: str
    preco: float
    categoria_id: int
    controlado: bool = False
    dose_maxima: Optional[float] = None
    estoque_minimo_emergencia: int = 0

class ProdutoCreate(ProdutoBase):
    pass

class Produto(ProdutoBase):
    id: int
    saldo_atual: int

    model_config = {"from_attributes": True}

class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    categoria_id: Optional[int] = None
    controlado: Optional[bool] = None
    dose_maxima: Optional[float] = None
    estoque_minimo_emergencia: Optional[int] = None

class MovimentacaoBase(BaseModel):
    produto_id: int
    tipo: str = Field(..., pattern="^(entrada|saida)$")
    quantidade: int = Field(..., gt=0)
    crm_medico: Optional[str] = None
    dose_prescrita: Optional[float] = None
    nome_paciente: Optional[str] = None

class MovimentacaoCreate(MovimentacaoBase):
    pass

class Movimentacao(MovimentacaoBase):
    id: int
    data_hora: datetime

    model_config = {"from_attributes": True}
