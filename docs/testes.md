# 🧪 Plano de Testes, Cenários Validados e Evidências (CP2 & CP3)

Este documento consolida a validação funcional, de regras de negócio e de integração ponta a ponta do sistema **VitalStock (API + Banco de Dados + Frontend/Dashboard + LLM)**.

---

## 1. Metodologia e Ferramentas de Automação
- **Framework de Testes Automatizados:** `pytest` + `FastAPI TestClient` (`httpx`)
- **Banco de Dados de Teste:** Instância isolada SQLite (`test_vitalstock.db`) criada e destruída automaticamente via fixture `setup_test_database` a cada execução da suíte, garantindo **idempotência** e **isolamento** em relação ao banco de produção.
- **Comando para Execução:**
  ```bash
  pytest -v
  ```

---

## 2. Matriz dos Cenários de Teste (Sucesso, Erro e Integração)

A suíte localizada em [`tests/test_vitalstock.py`](../tests/test_vitalstock.py) contempla **12 cenários automatizados** (superando o mínimo exigido de 5 cenários e 2 testes automatizados):

| ID | Cenário de Teste | Tipo | Endpoint / Componente | Entrada Principal | Resultado Esperado | Resultado Obtido | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CT-01** | Disponibilidade do Healthcheck e Interface Frontend | Integração | `GET /health` e `GET /` | Requisição HTTP GET | Retornar HTTP `200 OK` com JSON `"status": "healthy"` e HTML do Dashboard | HTTP `200 OK` em ambos os endpoints | ✅ PASSOU |
| **CT-02** | Cadastro e listagem de Categoria Hospitalar | Sucesso | `POST /api/v1/categorias/` | `{"nome": "Analgésicos Opióides Teste"}` | Criar registro no banco e retornar HTTP `201 Created` com `id: 1` | HTTP `201 Created` e listagem retornando a categoria | ✅ PASSOU |
| **CT-03** | Bloqueio de Categoria com nome duplicado | **Erro / Dado Inválido** | `POST /api/v1/categorias/` | `{"nome": "Analgésicos Opióides Teste"}` (repetido) | Rejeitar cadastro com HTTP `400 Bad Request` informando duplicidade | HTTP `400`: `"Categoria já cadastrada com este nome"` | ✅ PASSOU |
| **CT-04** | Cadastro de Medicamento Controlado com Saldo Inicial | Sucesso | `POST /api/v1/produtos/` | `Fentanil 0,05mg/ml`, `controlado: true`, `dose_maxima: 0.1`, `saldo_inicial: 15` | Criar produto com `saldo_atual: 15` e gerar movimentação inicial automática | HTTP `201 Created`, `saldo_atual = 15` | ✅ PASSOU |
| **CT-05** | **Trava ANVISA (Portaria 344):** Saída de Controlado sem CRM | **Erro / Regra de Negócio** | `POST /api/v1/movimentacoes/` | `tipo: "saida"`, `produto_id: 1` (Controlado), `crm_medico: null` | Bloquear saída imediatamente com HTTP `400 Bad Request` e preservar saldo | HTTP `400`: `"ALERTA DE SEGURANÇA: A saída de um medicamento controlado exige o CRM..."` | ✅ PASSOU |
| **CT-06** | **Trava Anti-Erro Médico:** Saída com Dose Prescrita Letal | **Erro / Regra de Negócio** | `POST /api/v1/movimentacoes/` | `tipo: "saida"`, `dose_prescrita: 0.85` (Limite seguro do Fentanil é `0.1mg`) | Bloquear saída com HTTP `400 Bad Request` impedindo overdose no paciente | HTTP `400`: `"ALERTA FATAL EVITADO: A dose prescrita (0.85mg) excede o limite MÁXIMO SEGURO (0.1mg)..."` | ✅ PASSOU |
| **CT-07** | **Trava de Estoque Físico:** Saída maior que o saldo disponível | **Erro / Regra de Negócio** | `POST /api/v1/movimentacoes/` | `tipo: "saida"`, `quantidade: 999` (Saldo atual: `15`) | Bloquear saída com HTTP `400 Bad Request` evitando estoque negativo | HTTP `400`: `"Saldo insuficiente no estoque do hospital."` | ✅ PASSOU |
| **CT-08** | Saída válida e disparo automático de Alerta de Ruptura Cirúrgica | Sucesso + Integração | `POST /api/v1/movimentacoes/` + `GET /api/v1/produtos/alertas-emergencia` | Retirada de `8` un. com `CRM-SP 123456` e `dose: 0.05mg` (Saldo cai de 15 para 7; mínimo é 10) | Registrar saída (`201`) e incluir o produto automaticamente no endpoint de alertas críticos | HTTP `201 Created`; `/alertas-emergencia` retorna Fentanil com `saldo_atual: 7` | ✅ PASSOU |
| **CT-09** | Filtros Otimizados da API e Dashboard Consolidado | Integração | `GET /api/v1/produtos/?controlado=true&apenas_alerta=true` e `GET /api/v1/dashboard/resumo` | Query params combinados | Retornar apenas produtos filtrados e KPIs consolidados em uma única chamada | HTTP `200 OK` com KPIs exatos e zero N+1 queries | ✅ PASSOU |
| **CT-10** | **Integração LLM + Banco:** Interpretação de relato cirúrgico válido com baixa automática | Sucesso + Integração IA | `POST /api/v1/ia/interpretar-relato` | Relato natural com `CRM-SP 55443`, `2 ampolas de Fentanil dose 0.05mg`, `executar_baixa_automatica: true` | IA extrai dados, aprova nas travas e desconta 2 unidades do banco (`saldo` vai de 7 para 5) | HTTP `200 OK`, `status_geral: "APROVADO"`, `baixas_realizadas: 1`, `saldo_atual: 5` | ✅ PASSOU |
| **CT-11** | **Segurança IA + LGPD:** Bloqueio de relato cirúrgico com overdose e anonimização de CPF | **Erro / Segurança IA** | `POST /api/v1/ia/interpretar-relato` + `GET /api/v1/ia/historico` | Relato contendo CPF `123.456.789-00` e dose letal de `2.5mg` de Fentanil | IA identifica overdose (`BLOQUEADO_DOSE_LETAL`), não altera saldo e mascara o CPF no log de auditoria | `status_geral: "BLOQUEADO_PELA_TRAVA_HOSPITALAR"`, CPF salvo como `***.***.***-** (CPF PROTEGIDO LGPD)` | ✅ PASSOU |
| **CT-12** | **Apoio à Decisão IA:** Parecer Executivo de Risco Cirúrgico | Sucesso + Integração IA | `POST /api/v1/ia/relatorio-inteligente` | Dados reais do estoque em alerta | Gerar diagnóstico executivo e lista de recomendações prioritárias de compra | HTTP `200 OK` com diagnóstico detalhado e cálculo de reposição | ✅ PASSOU |

---

## 3. Registro de Correções e Melhorias Realizadas nos Testes
Durante o ciclo de validação entre o CP1, CP2 e CP3, foram identificadas e corrigidas as seguintes situações:
1. **Validação de String Vazia no CRM (Corrigido):** No CP1, o envio de `"crm_medico": "   "` (apenas espaços em branco) passava pela verificação booleana simples. Foi corrigido em `estoque_service.py` utilizando `not movimentacao.crm_medico.strip()`, garantindo bloqueio rigoroso.
2. **Prevenção de Preço ou Quantidade Negativa no Cadastro (Corrigido):** Adicionadas restrições `Field(..., gt=0)` e `ge=0` nos schemas Pydantic (`estoque_schemas.py`), retornando erro `422 Unprocessable Entity` automaticamente antes mesmo de chegar ao banco.
3. **Proteção de Dados Sensíveis em Prompts de IA (Corrigido):** Implementada função `_anonimizar_dados_sensiveis_lgpd()` em `ia_service.py` que remove CPFs por expressão regular antes de transmitir o relato para a API externa da LLM e antes de gravar na tabela `historico_ia`.

---

## 4. Evidência de Execução da Suíte Automatizada (`pytest`)
Os relatórios completos de execução encontram-se salvos na pasta [`evidencias/`](../evidencias/):
- [`evidencias/relatorio_pytest.txt`](../evidencias/relatorio_pytest.txt)
- [`evidencias/evidencia_integracao_api_ia.json`](../evidencias/evidencia_integracao_api_ia.json)
