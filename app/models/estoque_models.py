from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    descricao = Column(String)

    produtos = relationship("Produto", back_populates="categoria")

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    nome = Column(String, index=True, nullable=False)
    preco = Column(Float, nullable=False)
    saldo_atual = Column(Integer, default=0, nullable=False)
    controlado = Column(Integer, default=0, nullable=False) # 0 para Falso, 1 para Verdadeiro (SQLite)
    dose_maxima = Column(Float, nullable=True) # Limite seguro para não matar o paciente
    estoque_minimo_emergencia = Column(Integer, default=0, nullable=False) # Gatilho de alerta de falta

    categoria = relationship("Categoria", back_populates="produtos")
    movimentacoes = relationship("Movimentacao", back_populates="produto")

class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    tipo = Column(String, nullable=False) # 'entrada' ou 'saida'
    quantidade = Column(Integer, nullable=False)
    crm_medico = Column(String, nullable=True) # Exigido apenas para saida de controlados
    dose_prescrita = Column(Float, nullable=True) # A dose que o médico receitou na saida
    nome_paciente = Column(String, nullable=True) # Para rastreabilidade
    data_hora = Column(DateTime, default=datetime.utcnow, nullable=False)

    produto = relationship("Produto", back_populates="movimentacoes")
