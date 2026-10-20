# 🐳 Guia de Containerização (Docker) e Deploy Econômico na AWS EC2 (CP3)

Este documento detalha os comandos de construção e execução via contêineres Docker e o passo a passo para publicação na **AWS (Amazon Web Services)** utilizando uma instância gratuita/econômica (**EC2 `t2.micro` ou `t3.micro` Free Tier**).

---

## 1. Containerização com Docker (`Dockerfile` e `compose.yaml`)

O serviço central do **VitalStock ERP** está containerizado na raiz do projeto ([`Dockerfile`](../Dockerfile) e [`compose.yaml`](../compose.yaml)), expondo na porta `8000`:
- **Aplicação Web & Dashboard Hospitalar:** `http://localhost:8000/`
- **Documentação Interativa OpenAPI (Swagger):** `http://localhost:8000/docs`
- **Healthcheck do Contêiner:** `http://localhost:8000/health`

### Comandos para Construção e Inicialização do Contêiner:

```bash
# 1. Construir a imagem e iniciar o contêiner em background com Docker Compose
docker compose up -d --build

# 2. Verificar evidência do contêiner em execução e status (healthy)
docker compose ps

# 3. Ou utilizando comandos Docker diretos:
docker build -t vitalstock-api:3.0 .
docker run -d --name vitalstock-container -p 8000:8000 -e APP_ENV=production vitalstock-api:3.0

# 4. Testar resposta do serviço
curl http://localhost:8000/health
```

---

## 2. Deploy na AWS EC2 (Forma Mais Econômica / Free Tier — Custo Zero)

O repositório inclui o script automatizado [`deploy_aws.sh`](../deploy_aws.sh), projetado para rodar em uma instância **AWS EC2 `t2.micro` ou `t3.micro` (Ubuntu 22.04/24.04 LTS ou Amazon Linux 2023)** dentro do nível gratuito (*AWS Free Tier* ou *AWS Academy Learner Lab*).

### Passo 1: Criar a Instância EC2 na AWS
1. No console da AWS, acesse **EC2** $\rightarrow$ **Launch instance**.
2. **Name:** `vitalstock-cp3-server`
3. **AMI (Sistema Operacional):** **Ubuntu Server 24.04 LTS** (Free tier eligible).
4. **Instance type:** **`t2.micro`** ou **`t3.micro`** (Free tier eligible — **custo US$ 0,00**).
5. **Security Group (Firewall):**
   - Marque **Allow SSH traffic** (porta `22`).
   - Clique em **Add security group rule** e adicione:
     - **Type:** `Custom TCP` | **Port range:** `8000` | **Source:** `0.0.0.0/0` (Anywhere IPv4).
6. Clique em **Launch instance** e depois em **Connect** (pode conectar direto pelo navegador usando a aba **EC2 Instance Connect**!).

### Passo 2: Rodar o Deploy Automático no Terminal da EC2
Assim que abrir o terminal preto da EC2 no navegador, copie e cole apenas este bloco:

```bash
git clone https://github.com/rodriguesassisrenan/vitalstock-cp1.git
cd vitalstock-cp1
chmod +x deploy_aws.sh
./deploy_aws.sh
```

*(O script instala o Docker e o Docker Compose sozinho, constrói a imagem, sobe o contêiner com volume persistente e já imprime na tela o link público `http://SEU_IP_PUBLICO:8000/` pronto para abrir!).*

### Passo 3: Como Configurar a Chave do Google Gemini na Apresentação
- **Sem expor nada no GitHub:** Abra o endereço `http://SEU_IP_PUBLICO_EC2:8000/` no navegador, clique no menu lateral em **"Automação Clínica (LLM)"**, cole a sua chave gerada no [Google AI Studio](https://aistudio.google.com/app/apikey) no campo **"Cole sua GEMINI_API_KEY"** e clique em **"Aplicar Chave Gemini"**.
- Ou, se preferir já subir com a chave direto no terminal da EC2:
  ```bash
  sudo GEMINI_API_KEY="AIzaSySuaChaveRealAqui" docker compose up -d
  ```
