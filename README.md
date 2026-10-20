# VitalStock

Controle de estoque para farmácia hospitalar e centro cirúrgico. Projeto da disciplina de Python da FIAP, entrega do Checkpoint 3.

## Integrantes

| Nome | RM |
| --- | --- |
| Gustavo Lino | 574157 |
| Renan de A. Rodrigues | 574049 |
| Lucas Lopes Arias | 570875 |
| Luany Teles | 569954 |

## Links

- Repositório: https://github.com/rodriguesassisrenan/vitalstock-cp1
- Trello: https://trello.com/invite/b/6aa07858cf22cef7e97177fb/ATTI9d4d66b9cbd5005694147045ecb10e0cE67414DC/vitalstock-cp1
- Deploy (AWS EC2): http://34.204.49.93:8000/ (Swagger em http://34.204.49.93:8000/docs, healthcheck em http://34.204.49.93:8000/health)
- Apresentação do CP3: [Apresentação/VitalStock_CP3.pdf](Apresentação/VitalStock_CP3.pdf)

## Tema e objetivo

Cirurgia cancelada porque faltou anestésico ou fio de sutura é um problema comum em hospital pequeno, e erro de dose na dispensação é outro. A ideia do VitalStock é que o estoque do centro cirúrgico só aceite uma saída se ela fizer sentido: tem saldo, a dose está dentro do limite cadastrado e, se o remédio for controlado, tem CRM de quem prescreveu.

Regras de negócio que a API aplica em toda saída de estoque:

1. Saldo: não sai mais do que tem.
2. Dose máxima: se o produto tem `dose_maxima`, a saída precisa informar `dose_prescrita` e ela não pode passar do limite.
3. Controlados (Portaria 344/98 da ANVISA): produto com `controlado = true` só sai com `crm_medico`.
4. Alerta de ruptura: produto com `saldo_atual <= estoque_minimo_emergencia` aparece no dashboard e em `/api/v1/produtos/alertas-emergencia`.
5. Produto com movimentações não pode ser excluído, para não perder o histórico de quem retirou o quê.

A parte de IA usa o Gemini para ler um relato cirúrgico em texto livre ("usamos 2 ampolas de fentanil 0,05 mg..."), achar os itens no catálogo e passar cada um pelas mesmas regras antes de dar baixa. Também gera um parecer de compras a partir dos itens em alerta.

## Arquitetura

```text
Navegador (HTML + JS + Chart.js)
        |
        v
FastAPI  ->  services (regras)  ->  SQLAlchemy  ->  SQLite (volume Docker)
                  |
                  v
             Gemini API (opcional)
```

```text
app/
  main.py            criação da API, healthcheck, arquivos estáticos
  core/              configuração (.env) e conexão com o banco
  models/            tabelas: categorias, fornecedores, produtos, movimentacoes, historico_ia
  schemas/           validação de entrada e saída (Pydantic)
  services/          regras de negócio e chamada ao Gemini
  api/v1/endpoints/  rotas REST
  static/            frontend e dashboard
tests/               testes automatizados (pytest)
docs/                testes, deploy, monetização, banco e IA
evidencias/          relatório do pytest e prints
aws/                 scripts de deploy na EC2
Dockerfile, compose.yaml
```

O frontend é servido pela própria API, então não precisa de servidor separado nem de CORS.

## Variáveis de ambiente

Modelo em [`.env.example`](.env.example). O arquivo `.env` real não vai para o Git.

| Variável | Para que serve | Padrão |
| --- | --- | --- |
| `APP_ENV` | `development` ou `production` | `development` |
| `DATABASE_URL` | conexão do banco | `sqlite:///./estoque.db` |
| `AUTO_SEED` | carrega dados de exemplo se o banco estiver vazio | `true` |
| `CORS_ORIGINS` | origens extras liberadas, separadas por vírgula | vazio |
| `GEMINI_API_KEY` | chave do Google AI Studio; sem ela a leitura de relatos usa um extrator por regras | vazio |
| `GEMINI_MODEL` | modelo do Gemini | `gemini-2.5-flash` |

## Como rodar

Local:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Testes:

```bash
pytest -v
```

Docker:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
docker compose exec vitalstock-api pytest -q
```

Deploy na AWS: ver [`docs/deploy_e_docker.md`](docs/deploy_e_docker.md). Pelo CloudShell é um comando só (`aws/cloudshell_criar_ec2.sh`).

## Principais endpoints

| Método | Rota | O que faz |
| --- | --- | --- |
| GET, POST | `/api/v1/categorias/` | listar e criar categorias |
| GET, PUT, DELETE | `/api/v1/categorias/{id}` | buscar, alterar, excluir |
| GET, POST | `/api/v1/produtos/` | listar (filtros `categoria_id`, `controlado`, `apenas_alerta`, `busca`, paginação) e criar |
| GET, PUT, DELETE | `/api/v1/produtos/{id}` | buscar, alterar, excluir |
| GET | `/api/v1/produtos/alertas-emergencia` | itens no estoque mínimo ou abaixo |
| GET, POST | `/api/v1/movimentacoes/` | histórico e registro de entrada/saída |
| GET | `/api/v1/dashboard/resumo` | tudo que o dashboard mostra, numa chamada |
| GET, POST | `/api/v1/dashboard/fornecedores` | fornecedores |
| POST | `/api/v1/ia/interpretar-relato` | lê relato cirúrgico e aplica as regras |
| POST | `/api/v1/ia/relatorio-inteligente` | parecer de compras |
| GET | `/api/v1/ia/historico` | últimas análises da IA |

Documentação completa no Swagger (`/docs`).

## Testes

17 testes automatizados em [`tests/test_vitalstock.py`](tests/test_vitalstock.py), com banco SQLite separado que é criado e apagado a cada execução. Cobrem CRUD, as quatro travas, filtros, dashboard, a leitura de relato com baixa, a máscara de CPF, a integração com o Gemini (com resposta simulada) e casos de erro como fornecedor inexistente e exclusão de produto com histórico. Cenários e resultados em [`docs/testes.md`](docs/testes.md); saída do pytest em [`evidencias/`](evidencias/).

## Monetização

Assinatura mensal para clínicas e hospitais pequenos, em três planos (R$ 890, R$ 1.990 e R$ 4.490). Com 25 clientes a receita fica em torno de R$ 45 mil por mês. Contas, custos e premissas em [`docs/monetizacao.md`](docs/monetizacao.md).

## Limitações conhecidas

- Não tem login. Qualquer pessoa com o link do deploy consegue cadastrar, dar saída e ver nomes de pacientes. Para uso real precisaria de autenticação e perfis (farmácia, enfermagem, gestão).
- SQLite atende a demonstração, mas com vários usuários ao mesmo tempo o certo seria PostgreSQL.
- Só o CPF é mascarado antes de ir para o Gemini e para o histórico. O nome do paciente é retirado do texto enviado ao Gemini, mas fica salvo nas movimentações.
- O extrator por regras (usado sem chave do Gemini) só reconhece frases parecidas com os exemplos.
- A dose máxima é um valor fixo por produto. Na prática depende de peso, idade e via de administração.
- No AWS Academy o IP da EC2 muda quando o laboratório é reiniciado.
