from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, index=True, nullable=False)
    descricao = Column(String(255), nullable=True)

    produtos = relationship("Produto", back_populates="categoria")


class Fornecedor(Base):
    # separado de produtos para não repetir nome/CNPJ do laboratório em cada item
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), unique=True, index=True, nullable=False)
    cnpj = Column(String(20), unique=True, nullable=True)
    contato_emergencia = Column(String(100), nullable=True)

    produtos = relationship("Produto", back_populates="fornecedor")


class Produto(Base):
    __tablename__ = "produtos"
    __table_args__ = (
        Index("ix_produtos_alerta_estoque", "saldo_atual", "estoque_minimo_emergencia"),
        Index("ix_produtos_categoria_controlado", "categoria_id", "controlado"),
    )

    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False, index=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True, index=True)
    nome = Column(String(150), index=True, nullable=False)
    lote = Column(String(50), default="LOTE-PADRAO", nullable=True)
    unidade_medida = Column(String(30), default="ampola", nullable=False)
    preco = Column(Float, nullable=False)
    saldo_atual = Column(Integer, default=0, nullable=False)
    controlado = Column(Integer, default=0, nullable=False)  # 0/1
    dose_maxima = Column(Float, nullable=True)  # mg por aplicação
    estoque_minimo_emergencia = Column(Integer, default=0, nullable=False)  # abaixo disso entra em alerta

    categoria = relationship("Categoria", back_populates="produtos")
    fornecedor = relationship("Fornecedor", back_populates="produtos")
    movimentacoes = relationship("Movimentacao", back_populates="produto", cascade="all, delete-orphan")


class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    __table_args__ = (
        Index("ix_movimentacoes_produto_data", "produto_id", "data_hora"),
    )

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, index=True)  # 'entrada' ou 'saida'
    quantidade = Column(Integer, nullable=False)
    crm_medico = Column(String(40), nullable=True)  # obrigatório na saída de controlados
    dose_prescrita = Column(Float, nullable=True)  # mg
    nome_paciente = Column(String(120), nullable=True)
    observacao = Column(String(255), nullable=True)
    data_hora = Column(DateTime, default=utc_now, nullable=False, index=True)

    produto = relationship("Produto", back_populates="movimentacoes")


class HistoricoIA(Base):
    # registro de cada chamada à IA: o que entrou (já sem CPF), o que saiu e qual modelo respondeu
    __tablename__ = "historico_ia"

    id = Column(Integer, primary_key=True, index=True)
    tipo_analise = Column(String(50), nullable=False)  # 'relato_cirurgico' ou 'relatorio_estoque'
    entrada_usuario = Column(Text, nullable=False)
    resposta_resumo = Column(Text, nullable=False)
    modelo_utilizado = Column(String(80), nullable=False)
    status_seguranca = Column(String(40), default="APROVADO", nullable=False)
    data_hora = Column(DateTime, default=utc_now, nullable=False)
