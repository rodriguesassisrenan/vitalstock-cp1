# Testes

## Como rodar

```bash
pytest -v
```

Ou dentro do contêiner: `docker compose exec vitalstock-api pytest -q`.

Os testes usam `pytest` com o `TestClient` do FastAPI e um banco SQLite próprio (`test_vitalstock.db`), criado no começo e apagado no fim. O banco da aplicação não é tocado. Os testes rodam em ordem e alguns dependem do estado deixado pelo anterior (por exemplo, o saldo do Fentanil).

## Cenários

| ID | Cenário | Tipo | Entrada | Esperado | Obtido |
| --- | --- | --- | --- | --- | --- |
| CT-01 | Healthcheck e frontend no ar | Integração | `GET /health` e `GET /` | 200 nos dois | 200 nos dois |
| CT-02 | Criar e listar categoria | Sucesso | `POST /categorias/` | 201 e categoria na listagem | 201 |
| CT-03 | Categoria com nome repetido | Erro | mesmo nome do CT-02 | 400 | 400, "Categoria já cadastrada com este nome" |
| CT-04 | Cadastrar controlado com saldo inicial | Sucesso | Fentanil, `controlado: true`, `dose_maxima: 0.1`, `saldo_inicial: 15` | 201, saldo 15 | 201, saldo 15 |
| CT-05 | Saída de controlado sem CRM | Erro (regra) | `crm_medico: null` | 400 | 400, saldo inalterado |
| CT-06 | Saída com dose acima do máximo | Erro (regra) | `dose_prescrita: 0.85` (máx. 0.1) | 400 | 400 |
| CT-07 | Saída maior que o saldo | Erro (regra) | `quantidade: 999` | 400 | 400, "Saldo insuficiente" |
| CT-08 | Saída válida que gera alerta | Sucesso + integração | 8 un., CRM e dose 0.05 | 201 e produto em `/alertas-emergencia` | saldo 7, produto listado |
| CT-09 | Filtros e dashboard | Integração | `?controlado=true&apenas_alerta=true` e `/dashboard/resumo` | só os filtrados; KPIs certos | ok |
| CT-10 | Relato cirúrgico com baixa automática | Integração IA + banco | relato com CRM e "2 ampolas de Fentanil dose 0.05mg" | APROVADO, saldo 7 para 5 | ok |
| CT-11 | Relato com overdose e CPF | Erro + segurança | relato com CPF e dose 2.5 mg | bloqueado, sem baixa, CPF mascarado no histórico | ok |
| CT-12 | Parecer de compras | Sucesso IA | itens em alerta | risco MODERADO/CRITICO com recomendação | ok |
| CT-13 | Saída sem dose de item com dose máxima | Erro (regra) | saída de Fentanil sem `dose_prescrita` | 400 | 400 |
| CT-14 | Produto com fornecedor inexistente | Erro (dado inválido) | `fornecedor_id: 999` | 404 | 404 |
| CT-15 | Excluir produto com histórico | Erro (regra) | `DELETE /produtos/1` | 409 e produto continua | 409 |
| CT-16 | Rota para trocar a chave do LLM | Segurança | `POST /ia/configurar-chave` | rota não existe | 404/405 |
| CT-17 | Integração com o Gemini (resposta simulada) | Integração LLM | relato com nome e CPF, Gemini simulado | chave no header, nome e CPF fora do prompt, resposta passa pelas travas | ok |

Resultado: 17 passed. Saída completa em [`evidencias/relatorio_pytest.txt`](../evidencias/relatorio_pytest.txt).

O CT-17 não chama o Gemini de verdade (o teste não pode depender de chave nem de internet). A chamada real foi conferida no deploy; ver prints em `evidencias/`.

## Falhas encontradas e correções

| Problema | Como apareceu | Correção |
| --- | --- | --- |
| CRM só com espaços passava como válido | teste manual no Swagger | `crm_medico.strip()` na validação |
| Preço e quantidade negativos aceitos | teste manual | `Field(gt=0)` / `ge=0` nos schemas, erro 422 |
| CPF ia para o Gemini e para o histórico | revisão do código | máscara de CPF antes de qualquer envio ou gravação |
| Saída de controlado sem dose passava pela trava de dose | revisão do código | dose obrigatória quando o produto tem `dose_maxima` (CT-13) |
| `fornecedor_id` inexistente gerava erro 500 | teste manual | validação no service (404) e handler de `IntegrityError` (409) (CT-14) |
| Excluir produto apagava o histórico de saídas | teste manual | exclusão bloqueada com 409 (CT-15) |
| Qualquer pessoa podia trocar a chave do Gemini pela rota `/ia/configurar-chave` | revisão de segurança | rota removida; chave só por variável de ambiente (CT-16) |
| Nome de produto com HTML era executado no dashboard (XSS) | teste manual com `<img src=x onerror=alert(1)>` | função `esc()` no `app.js` antes de montar o HTML |
| `pytest -v` falhava com `No module named 'app'` fora do Windows | rodando em Linux | `pytest.ini` com `pythonpath = .` |
| No servidor, com `GEMINI_API_KEY` configurada, o CT-11 falhava porque o teste chamava o Gemini real e a resposta variava | `pytest` rodando dentro do contêiner na EC2 | os testes desligam a chave real no início; a integração com o Gemini fica coberta pelo CT-17 com resposta simulada |
