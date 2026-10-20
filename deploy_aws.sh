#!/bin/bash
# ==============================================================================
# VITALSTOCK ERP - SCRIPT DE DEPLOY AUTOMÁTICO E ECONÔMICO NA AWS EC2 (FREE TIER)
# Compatível com: Ubuntu 22.04 / 24.04 LTS ou Amazon Linux 2023 (t2.micro / t3.micro)
# Custo na AWS Free Tier / AWS Academy Learner Lab: US$ 0.00
# ==============================================================================
set -e

echo "=== [1/4] Instalando Docker, Docker Compose e Git ==="
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y docker.io docker-compose-v2 git curl
elif command -v dnf &> /dev/null; then
    sudo dnf update -y
    sudo dnf install -y docker git curl
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

sudo systemctl enable docker
sudo systemctl start docker

echo "=== [2/4] Preparando diretório da aplicação ==="
if [ ! -f "compose.yaml" ]; then
    REPO_URL="${1:-https://github.com/rodriguesassisrenan/vitalstock-cp1.git}"
    rm -rf vitalstock-deploy
    git clone "$REPO_URL" vitalstock-deploy
    cd vitalstock-deploy
fi

echo "=== [3/4] Construindo imagem e iniciando contêiner na porta 8000 ==="
sudo GEMINI_API_KEY="${GEMINI_API_KEY:-}" docker compose up -d --build

echo "=== [4/4] Verificando saúde do serviço ==="
sleep 4
sudo docker compose ps
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "SEU_IP_PUBLICO_EC2")
echo "=================================================================="
echo "DEPLOY CONCLUÍDO COM SUCESSO NA AWS!"
echo "Dashboard e Frontend : http://${PUBLIC_IP}:8000/"
echo "Documentação Swagger : http://${PUBLIC_IP}:8000/docs"
echo "Healthcheck          : http://${PUBLIC_IP}:8000/health"
echo "=================================================================="
