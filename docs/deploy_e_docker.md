# Docker e deploy na AWS

A aplicação roda num contêiner só (API + frontend). O banco SQLite fica num volume do Docker (`vitalstock_data`), então os dados continuam lá quando o contêiner é recriado.

## Docker local

```bash
docker compose up -d --build
docker compose ps                     # STATUS deve mostrar (healthy)
curl http://localhost:8000/health
docker compose exec vitalstock-api pytest -q
docker compose logs --tail 20
```

Sem compose:

```bash
docker build -t vitalstock-api .
docker run -d --name vitalstock -p 8000:8000 --env-file .env vitalstock-api
```

O contêiner roda com um usuário sem privilégio de root (`appuser`) e tem `HEALTHCHECK` chamando `/health`.

## Deploy na AWS pelo CloudShell

O script [`aws/cloudshell_criar_ec2.sh`](../aws/cloudshell_criar_ec2.sh) faz tudo a partir do CloudShell do console da AWS:

```bash
git clone https://github.com/rodriguesassisrenan/vitalstock-cp1.git
cd vitalstock-cp1
bash aws/cloudshell_criar_ec2.sh
```

O que ele faz:

1. Pede a chave do Gemini sem mostrar na tela (pode deixar em branco).
2. Busca a AMI oficial do Ubuntu 24.04.
3. Cria o security group `vitalstock-sg` liberando só a porta 8000. Não abre SSH.
4. Cria uma EC2 `t3.micro` com disco criptografado, IMDSv2 obrigatório e, no AWS Academy, o perfil padrão `LabInstanceProfile`.
5. No primeiro boot (user-data) a máquina instala Docker, clona o repositório, grava o `.env` com permissão 600 e roda `docker compose up -d --build`.
6. Espera `/health` responder e mostra o link.

Cuidados de segurança adotados:

- Nenhuma chave de acesso da AWS (Access Key) é criada ou usada; o CloudShell já usa a sessão do console.
- A chave do Gemini não fica no Git nem no histórico do terminal. Ela fica no `.env` da instância e no user-data, que só quem tem acesso à conta AWS consegue ler. Depois da avaliação a chave deve ser revogada no Google AI Studio.
- A única porta aberta para a internet é a 8000.

Se não responder em 10 minutos, o script mostra o log de inicialização da máquina (`get-console-output`).

Para desligar: `aws ec2 terminate-instances --instance-ids <id mostrado pelo script>`.

## Deploy manual numa EC2 já criada

Com uma EC2 Ubuntu e acesso ao terminal dela (EC2 Instance Connect ou SSH):

```bash
git clone https://github.com/rodriguesassisrenan/vitalstock-cp1.git
cd vitalstock-cp1
cp .env.example .env
nano .env                 # preencher GEMINI_API_KEY
bash aws/deploy_ec2.sh
```

## Como verificar o deploy

- `http://IP:8000/health` responde `{"status": "healthy", ...}` e o campo `llm` mostra o modelo do Gemini quando a chave foi configurada.
- `http://IP:8000/docs` abre o Swagger.
- `http://IP:8000/` abre o dashboard com os dados de exemplo.

No AWS Academy o laboratório desliga a instância quando a sessão acaba, e o IP público muda ao ligar de novo. Antes de apresentar, ligar o lab, conferir o IP em EC2 > Instances e atualizar o link se for preciso.
