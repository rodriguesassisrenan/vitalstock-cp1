FROM python:3.11-slim

LABEL maintainer="Grupo VitalStock - FIAP"
LABEL description="Container oficial da aplicação VitalStock (API FastAPI + Dashboard + IA LLM)"

# Evita criação de arquivos .pyc e garante logs em tempo real no container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:///./data/estoque.db \
    AUTO_SEED=true \
    PORT=8000

WORKDIR /app

# Instala dependências do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Cria diretório persistente para o banco SQLite
RUN mkdir -p /app/data

# Copia o código da aplicação e a suíte de testes
COPY app ./app
COPY tests ./tests

EXPOSE 8000

# Healthcheck integrado validando se o serviço responde na porta 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
