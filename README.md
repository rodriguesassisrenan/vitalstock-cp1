# Gestor de Estoque API

## Descrição
Esta é a entrega do Checkpoint 1 (CP1). Trata-se de uma API REST desenvolvida em Python (FastAPI) para controle e gestão inteligente de insumos hospitalares. O sistema ("VitalStock") permite o cadastro de categorias e medicamentos, registrando movimentações em tempo real e garantindo a segurança operacional do hospital.

## O Problema: A Crise Invisível nos Hospitais
A falta de insumos (anestésicos, fios de sutura, medicamentos vitais) é uma das maiores causas de **cancelamento de cirurgias de urgência e oncológicas no Brasil**. Por outro lado, estudos indicam que até 20% dos medicamentos em hospitais são desperdiçados por passarem da validade devido à falta de gestão de estoque. Furos no estoque não significam apenas prejuízo financeiro, mas **risco direto à vida dos pacientes** que já estão no bloco cirúrgico.

## A Solução Proposta (VitalStock)
O **VitalStock** atua como uma API blindada que garante a integridade dos dados de farmácias hospitalares e blocos cirúrgicos. Através de travas de software estritas, o sistema impede o registro de saídas fantasmas e bloqueia retiradas caso o saldo seja insuficiente, garantindo que o estoque digital reflita a realidade física.

**O Futuro (CP2/CP3):** Como evolução da arquitetura, o VitalStock será integrado a agentes de Inteligência Artificial (LLMs). O objetivo é que médicos ou enfermeiros chefes relatem a conclusão de um procedimento cirúrgico por áudio ou texto natural, e a IA deduza e baixe automaticamente do estoque os medicamentos e descartáveis utilizados, eliminando o erro humano do processo.

## Principais Funcionalidades e Regras de Negócio
- Cadastro, leitura, atualização e exclusão (CRUD) de Categorias e Produtos.
- Registro de Movimentações (entrada e saída).
- Endpoint para Relatório de Alertas (Prevenção de suspensão de cirurgias).
- **Regras de Negócio (Travas Hospitalares):**
  1. **Trava de Dosagem Segura (Anti-Erro Médico):** O sistema impede que enfermeiros registrem a saída de uma dosagem letal. Se a `dose_prescrita` na movimentação for maior que a `dose_maxima` cadastrada para o medicamento, a API bloqueia a saída na hora para salvar a vida do paciente.
  2. **Trava de Medicamentos Controlados (ANVISA):** Se um medicamento for marcado como `controlado = true`, o sistema exige obrigatoriamente o preenchimento do `crm_medico`. Caso contrário, a API bloqueia a ação.
  3. **Trava de Estoque Físico:** É proibido registrar uma movimentação de "saída" se a quantidade solicitada for maior que o saldo atual do produto.
  4. **Alerta de Ruptura (Emergência):** Os produtos possuem um `estoque_minimo_emergencia`. Um endpoint exclusivo lista os medicamentos que estão perto de acabar, permitindo ação rápida da gestão hospitalar.

## Entidades Principais do Sistema
- **Categoria:** Agrupa produtos por similaridade (ex: "Bebidas", "Ingredientes"). Atributos: `id`, `nome` (único), `descricao`.
- **Produto:** Item controlado pelo estoque. Atributos: `id`, `categoria_id` (FK), `nome`, `preco`, `saldo_atual`.
- **Movimentacao:** Registro de alteração de saldo. Atributos: `id`, `produto_id` (FK), `tipo` ('entrada' ou 'saida'), `quantidade`, `data_hora`.

## Integrantes do Grupo
- [NOME DOS INTEGRANTES]

## Tecnologias Utilizadas e Arquitetura Inicial
- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **ORM e Validação:** SQLAlchemy, Pydantic v2
- **Arquitetura Inicial:** Estruturada em camadas para facilitar a manutenção:
  - `api/v1/`: Define os endpoints, roteadores e métodos HTTP.
  - `services/`: Contém as regras de negócio e integrações com o banco.
  - `models/`: Mapeamento das tabelas do banco de dados (SQLAlchemy).
  - `schemas/`: Classes de validação de dados de requisição/resposta (Pydantic).
  - `core/`: Configurações centrais do sistema.

## Banco de Dados Utilizado
- **Banco de Dados:** SQLite
(Escolhido para o CP1 pela facilidade de execução local e por não requerer dependências externas complexas para avaliação).

## Configuração das Variáveis de Ambiente
Para este CP1, **não há variáveis de ambiente sensíveis ou arquivos `.env` necessários**. O banco de dados SQLite roda de forma totalmente local e a URL de conexão já está configurada diretamente no código (`sqlite:///./estoque.db`). 

## Instruções de Instalação e Execução
1. **Clone o repositório:**
```bash
git clone https://github.com/[SEU_USUARIO]/[NOME_DO_REPOSITORIO].git
cd [NOME_DO_REPOSITORIO]
```
2. **(Opcional) Crie e ative um ambiente virtual:**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```
3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```
4. **Inicie o servidor local:**
```bash
uvicorn app.main:app --reload
```
A API estará rodando em `http://127.0.0.1:8000`. As tabelas do banco de dados são criadas automaticamente na primeira execução.

## Principais Endpoints
A API disponibiliza endpoints para cada entidade. Exemplos:
- **GET** `/api/v1/produtos/` - Lista todos os produtos
- **POST** `/api/v1/categorias/` - Cria uma nova categoria
- **PUT** `/api/v1/produtos/{id}` - Atualiza dados de um produto existente
- **DELETE** `/api/v1/categorias/{id}` - Exclui uma categoria (se não houver produtos vinculados)
- **POST** `/api/v1/movimentacoes/` - Registra uma nova entrada ou saída de estoque

## Link para Documentação Swagger
A documentação interativa e completa (Swagger UI) é gerada automaticamente pelo FastAPI. Após iniciar a API, acesse:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

## Link do Trello/Notion
[LINK DO TRELLO]
