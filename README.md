# VitalStock ERP — Gestão de Farmácia Hospitalar e Bloco Cirúrgico (CP3)

> **Sistema Integrado de Controle de Insumos Cirúrgicos, Travas Clínicas (ANVISA Portaria 344/98 e Anti-Overdose), Dashboard Hospitalar e Automação Clínica com LLM.**

---

## Integrantes do Grupo
- **Gustavo Lino** — RM: `574157`
- **Renan de A. Rodrigues** — RM: `574049`
- **Lucas Lopes Arias** — RM: `570875`
- **Luany Teles** — RM: `569954`

---

## Links do Projeto
- **Repositório GitHub:** [https://github.com/rodriguesassisrenan/vitalstock-cp1](https://github.com/rodriguesassisrenan/vitalstock-cp1)
- **Quadro Ágil (Trello):** [https://trello.com/invite/b/6aa07858cf22cef7e97177fb/ATTI9d4d66b9cbd5005694147045ecb10e0cE67414DC/vitalstock-cp1](https://trello.com/invite/b/6aa07858cf22cef7e97177fb/ATTI9d4d66b9cbd5005694147045ecb10e0cE67414DC/vitalstock-cp1)
- **Ambiente de Deploy (AWS EC2 Docker):** Configurado via [`deploy_aws.sh`](deploy_aws.sh) na porta `8000` (instruções de acesso e verificação em [`docs/deploy_e_docker.md`](docs/deploy_e_docker.md))
- **Interface Web & Dashboard:** `http://localhost:8000/` (ou `http://<IP_PUBLICO_AWS_EC2>:8000/`)
- **Documentação Swagger OpenAPI:** `http://localhost:8000/docs`
- **Healthcheck do Serviço:** `http://localhost:8000/health`

---

## Tema, Problema e Objetivo da Solução

A falta de insumos críticos (anestésicos venosos, opióides, fios de sutura) é uma das principais causas de **cancelamento de cirurgias de urgência no Brasil**, enquanto erros de dosagem na dispensação hospitalar e falhas no controle de medicamentos da **Portaria 344/98 (ANVISA)** geram graves riscos à vida do paciente.

O **VitalStock ERP** resolve esse problema integrando uma API RESTful em Python/FastAPI, banco de dados relacional normalizado (3FN), interface visual de gestão farmacêutica com Dashboard em tempo real e integração com **Large Language Model (Google Gemini API)** acoplada a **4 travas de segurança hospitalar**:
1. **Trava de Dosagem Segura (Anti-Overdose):** Bloqueia saídas cuja `dose_prescrita` exceda a `dose_maxima` segura cadastrada para o medicamento.
2. **Trava da ANVISA (Portaria 344/98):** Exige obrigatoriamente o preenchimento do `crm_medico` para retirada de medicamentos controlados (`controlado = true`).
3. **Trava de Estoque Físico:** Impede saídas superiores ao `saldo_atual` disponível no hospital.
4. **Alerta de Ruptura Cirúrgica:** Monitora continuamente os insumos com `saldo_atual <= estoque_minimo_emergencia`.
5. **Automação Clínica com LLM (`/api/v1/ia/interpretar-relato` e `/api/v1/ia/relatorio-inteligente`):** Lê relatos pós-operatórios em texto livre, anonimiza CPFs em conformidade com a LGPD, extrai medicamentos/doses/CRM, valida nas travas clínicas antes da baixa automática e emite parecer de ressuprimento.

---

## Visão Geral da Arquitetura e Estrutura de Pastas (Padrão CP3)

```text
CP3/
├── src/ (e app/)                 # Código-fonte da aplicação (FastAPI + SQLAlchemy + Frontend ERP)
│   ├── main.py                   # Inicialização da API, CORS, Seed inicial, StaticFiles e /health
│   ├── core/                     # Configurações (.env) e conexão SQLite com PRAGMA foreign_keys=ON
│   ├── models/                   # Modelagem 3FN: Categoria, Fornecedor, Produto, Movimentacao, HistoricoIA
│   ├── schemas/                  # Contratos e validações de entrada/saída (Pydantic v2)
│   ├── services/                 # Regras de negócio, travas hospitalares e integração Google Gemini LLM
│   ├── api/v1/endpoints/         # Rotas REST (/categorias, /produtos, /movimentacoes, /dashboard, /ia)
│   └── static/                   # Interface Frontend + Dashboard Hospitalar (HTML5, CSS3, JS + Chart.js)
├── tests/
│   └── test_vitalstock.py        # 12 testes automatizados (pytest + FastAPI TestClient)
├── docs/
│   ├── testes.md                 # Cenários de teste (sucesso, erro e integração) e correções realizadas
│   ├── monetizacao.md            # Proposta de monetização B2B SaaS, preços, custos operacionais e viabilidade
│   ├── deploy_e_docker.md        # Guia de containerização Docker e deploy na AWS EC2
│   └── evolucao_cp2_banco_e_ia.md# Documentação da normalização do banco, otimização de API e LLM
├── evidencias/                   # Relatório do pytest e prints de execução e funcionamento
├── Dockerfile                    # Containerização do serviço principal
├── compose.yaml                  # Orquestração Docker Compose com volume persistente e healthcheck
├── deploy_aws.sh                 # Script de provisionamento e deploy em 1 comando na AWS EC2
├── .env.example                  # Exemplo de variáveis de ambiente (sem exposição de segredos)
└── requirements.txt              # Dependências Python
```

---

## Variáveis de Ambiente (Sem Exposição de Segredos)

Configuradas via arquivo `.env` ou variáveis do contêiner Docker (modelo em [`.env.example`](.env.example)):
- `APP_ENV`: Ambiente de execução (`development` ou `production`).
- `DATABASE_URL`: Caminho de persistência do banco (`sqlite:///./estoque.db` local ou `sqlite:///./data/estoque.db` no contêiner).
- `AUTO_SEED`: Quando `true`, popula o catálogo inicial caso o banco esteja vazio.
- `GEMINI_API_KEY`: Chave da API Google Gemini (configurada apenas no servidor AWS ou na interface web durante a demonstração, nunca exposta no GitHub).
- `GEMINI_MODEL`: Modelo utilizado (`gemini-2.5-flash`).

---

## Comandos para Instalação, Testes e Execução com Docker

### 1. Execução Local
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Execução dos Testes Automatizados (`pytest`)
```bash
pytest -v
```

### 3. Execução com Docker / Docker Compose
```bash
# Construir imagem e iniciar contêiner
docker compose up -d --build

# Verificar contêiner em execução e healthcheck
docker compose ps
curl http://localhost:8000/health
```

### 4. Deploy na AWS EC2 (Free Tier)
```bash
chmod +x deploy_aws.sh
./deploy_aws.sh
```

---

## Resumo dos Testes e Resultados ([`docs/testes.md`](docs/testes.md))

Foram elaborados e automatizados **12 cenários de teste** em [`tests/test_vitalstock.py`](tests/test_vitalstock.py) (log completo em [`evidencias/relatorio_pytest.txt`](evidencias/relatorio_pytest.txt)), cobrindo:
- **Sucesso e Integração:** Healthcheck e Frontend (`CT-01`), CRUD de Categorias (`CT-02`), Cadastro de Controlados com Saldo Inicial (`CT-04`), Saída Válida com disparo de Alerta Cirúrgico (`CT-08`), Filtros e Dashboard Consolidado (`CT-09`), Baixa Automática por Relato Cirúrgico IA (`CT-10`) e Parecer de Compras IA (`CT-12`).
- **Cenários de Erro e Travas Hospitalares:** Bloqueio de Categoria Duplicada (`CT-03`), Bloqueio ANVISA para saída de controlado sem CRM (`CT-05`), Bloqueio Anti-Overdose para dose prescrita acima do limite (`CT-06`), Bloqueio de Estoque Físico Insuficiente (`CT-07`) e Bloqueio de Overdose no Relato IA com anonimização de CPF pela LGPD (`CT-11`).
- **Resultado Obtido:** `12 passed in 0.76s` (100% de aprovação).

---

## Proposta de Monetização ([`docs/monetizacao.md`](docs/monetizacao.md))

- **Público-Alvo:** Clínicas cirúrgicas ambulatoriais (*Day Hospitals*) e hospitais de pequeno/médio porte (20 a 150 leitos).
- **Modelo de Receita:** **Assinatura Mensal B2B SaaS em Tiers** (*VitalStock Clinic*: R\$ 890/mês | *Hospital Pro*: R\$ 1.990/mês | *Enterprise*: R\$ 4.490/mês).
- **Simulação Financeira (Cenário de 25 instituições clientes):**
  - **Faturamento Mensal Recorrente (MRR):** `R$ 45.550,00 / mês` (`R$ 546.600,00 / ano`)
  - **Custos Operacionais Mensais (Cloud AWS + Banco + API Gemini + Manutenção/Suporte + Impostos):** `R$ 10.871,75 / mês`
  - **Resultado Líquido Mensal:** `R$ 34.678,25 / mês` (**Margem Líquida de 76,1%**; ponto de equilíbrio com apenas 4 hospitais).
