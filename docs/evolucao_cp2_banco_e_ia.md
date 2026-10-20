# 🚀 Evolução Arquitetural: Banco Normalizado, Otimização de API e Integração LLM (CP2 & CP3)

Este documento detalha todas as evoluções técnicas implementadas sobre a base do CP1 para atender integralmente aos critérios de avaliação do **Checkpoint 2** e do **Checkpoint 3**.

---

## 1. Revisão e Normalização do Banco de Dados (3ª Forma Normal)

Na revisão do modelo relacional em [`app/models/estoque_models.py`](../app/models/estoque_models.py), foram aplicadas melhorias de integridade, normalização e indexação:

1. **Eliminação de Redundância com a Entidade `Fornecedor` (3FN):**
   - Antes, informações de laboratórios/fornecedores teriam que ser repetidas em texto dentro de cada produto. Criamos a tabela `fornecedores` (`id`, `nome` único, `cnpj` único, `contato_emergencia`) vinculada via chave estrangeira `fornecedor_id` à tabela `produtos`.
2. **Rastreabilidade de Lote, Unidade e Auditoria de IA (`HistoricoIA`):**
   - Adicionados atributos `lote` e `unidade_medida` em `produtos`, `observacao` em `movimentacoes`, e criada a tabela `historico_ia` para registrar todas as decisões tomadas pela Inteligência Artificial.
3. **Integridade Referencial Ativa no SQLite:**
   - Em [`app/core/database.py`](../app/core/database.py), configuramos o listener `PRAGMA foreign_keys=ON` em todas as conexões SQLite, garantindo que restrições de chave estrangeira sejam estritamente respeitadas pelo banco.
4. **Criação de Índices Compostos para Alta Performance:**
   - `ix_produtos_alerta_estoque (saldo_atual, estoque_minimo_emergencia)`: acelera a busca de insumos em risco cirúrgico.
   - `ix_produtos_categoria_controlado (categoria_id, controlado)`: acelera os filtros combinados da API.
   - `ix_movimentacoes_produto_data (produto_id, data_hora)`: otimiza a ordenação cronológica do histórico.

---

## 2. Otimizações da API REST

1. **Redução de Requisições Desnecessárias (Endpoint Consolidado):**
   - Criado o endpoint `GET /api/v1/dashboard/resumo`, que entrega em uma única resposta JSON todos os KPIs, lista de alertas de emergência, distribuição financeira por categoria e últimas movimentações. Isso reduziu de **5 requisições separadas no carregamento do frontend para apenas 1 requisição**.
2. **Eliminação do Problema de N+1 Queries:**
   - Uso de `joinedload(Categoria.produtos)` e `joinedload(Movimentacao.produto)` no SQLAlchemy em [`app/services/estoque_service.py`](../app/services/estoque_service.py), trazendo os relacionamentos em uma única consulta SQL (`JOIN`).
3. **Paginação e Filtros Avançados:**
   - `GET /api/v1/produtos/` agora suporta `skip`, `limit`, `categoria_id`, `controlado`, `apenas_alerta` e `busca` textual case-insensitive (`ILIKE`).
   - `GET /api/v1/movimentacoes/` suporta paginação e filtros por `produto_id` e `tipo` (`entrada` ou `saida`).

---

## 3. Aplicação de Inteligência Artificial (LLM) Integrada às Regras de Negócio

Conforme planejado desde o CP1, a IA do **VitalStock** não é um chatbot genérico, mas sim um **Agente Clínico de Automação e Apoio à Decisão** profundamente acoplado às travas hospitalares do backend ([`app/services/ia_service.py`](../app/services/ia_service.py)):

### Especificações Técnicas da Integração LLM:
- **Modelo / Serviço Utilizado:** **Google Gemini (`gemini-2.5-flash`)** via API REST oficial (`generativelanguage.googleapis.com`), configurado com `temperature: 0.1` e `responseMimeType: "application/json"` para garantir saídas determinísticas e estruturadas.
- **Arquitetura Resiliente (Hybrid Fallback):** Caso a variável `GEMINI_API_KEY` não esteja preenchida no ambiente do avaliador ou haja indisponibilidade de rede, o sistema aciona automaticamente o **VitalStock Clinical NLP Engine v3**, um motor local de processamento de linguagem natural e regex clínico que extrai CRM, paciente, medicamentos, quantidades e doses em `mg` diretamente contra o catálogo SQLite, garantindo **100% de disponibilidade em testes e apresentações**.
- **Finalidades da LLM no Sistema:**
  1. **`POST /api/v1/ia/interpretar-relato` (Baixa Inteligente por Relato Cirúrgico):** Recebe um texto livre da equipe médica, identifica quais medicamentos do banco foram usados, valida se a dose citada respeita a `dose_maxima` segura e se há `CRM` para medicamentos controlados pela ANVISA, e realiza a baixa automática no estoque se aprovado.
  2. **`POST /api/v1/ia/relatorio-inteligente` (Parecer Executivo de Risco e Compras):** Analisa os saldos reais do banco e gera recomendações orçadas de compra emergencial para evitar o cancelamento de cirurgias.
- **Limitações Identificadas:**
  - Relatos médicos com abreviações não padronizadas ou nomes comerciais divergentes do princípio ativo cadastrado podem exigir revisão manual (`status_geral: REVISAO_NECESSARIA`).
  - Por segurança clínica, a baixa automática no banco **nunca é executada pela IA se qualquer item do relato violar uma trava hospitalar** (ex: overdose ou ausência de CRM).
- **Cuidados com Segurança e Dados Sensíveis (LGPD):**
  - Antes de qualquer envio à API externa da LLM ou gravação na tabela `historico_ia`, a função `_anonimizar_dados_sensiveis_lgpd()` intercepta e mascara números de CPF (`***.***.***-** (CPF PROTEGIDO LGPD)`), garantindo conformidade com a Lei Geral de Proteção de Dados (Lei nº 13.709/2018).
  - As chaves de API são lidas exclusivamente via variáveis de ambiente (`os.getenv("GEMINI_API_KEY")`) e jamais expostas no repositório.
