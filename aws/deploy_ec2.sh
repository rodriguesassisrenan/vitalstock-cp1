#!/bin/bash
# Roda DENTRO de uma EC2 Ubuntu já criada: instala o Docker e sobe a aplicação.
# A chave do Gemini vai no arquivo .env desta pasta (veja .env.example), nunca no Git.
set -euo pipefail

if ! command -v docker &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y docker.io docker-compose-v2 git curl
    sudo systemctl enable --now docker
fi

if [ ! -f compose.yaml ]; then
    echo "Rode este script na raiz do projeto (onde está o compose.yaml)."
    exit 1
fi

[ -f .env ] && chmod 600 .env

# o compose lê o .env sozinho; não passar variáveis aqui, senão elas sobrescrevem o .env
sudo docker compose up -d --build

echo "Aguardando o healthcheck..."
for i in $(seq 1 30); do
    if curl -fs http://localhost:8000/health > /dev/null; then
        break
    fi
    sleep 3
done
sudo docker compose ps

IP=$(curl -s https://checkip.amazonaws.com || echo "IP_PUBLICO")
echo "Aplicação: http://${IP}:8000/"
echo "Swagger:   http://${IP}:8000/docs"
echo "Health:    http://${IP}:8000/health"
