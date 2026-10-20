# Banco, otimizações da API e uso do LLM

O que mudou desde o CP1 na modelagem, na API e o que foi acrescentado com IA.

## Banco de dados

Modelo em [`app/models/estoque_models.py`](../app/models/estoque_models.py).

Tabelas: `categorias`, `fornecedores`, `produtos`, `movimentacoes` e `historico_ia`.

- `fornecedores` saiu de dentro de `produtos`. Antes o nome do laboratório teria que ser repetido em cada item; agora o produto aponta para o fornecedor por `fornecedor_id` (nome e CNPJ únicos).
- `produtos` ganhou `lote`, `unidade_medida`, `controlado`, `dose_maxima` e `estoque_minimo_emergencia`. O saldo fica em `saldo_atual` e só muda por movimentação.
- `movimentacoes` guarda quem prescreveu (`crm_medico`), a dose, o paciente e a origem (manual ou relato da IA).
- `historico_ia` registra cada análise da IA: texto de entrada (já com CPF mascarado), resumo da resposta, modelo usado e resultado.
- O SQLite só respeita chave estrangeira com `PRAGMA foreign_keys=ON`, ligado em toda conexão em [`app/core/database.py`](../app/core/database.py). Categoria com produto não pode ser excluída (`RESTRICT`) e produto com movimentação também não (regra no service, para manter o histórico dos controlados).

Índices criados além das chaves:

- `movimentacoes (produto_id, data_hora)`: histórico de um produto em ordem de data, que é a consulta mais comum.
- `produtos (categoria_id, controlado)`: filtro combinado da listagem.
- `produtos (saldo_atual, estoque_minimo_emergencia)`: ajuda pouco, porque a consulta de alerta compara as duas colunas entre si. Com o volume do projeto não faz diferença; num banco grande valeria uma coluna calculada `em_alerta` com índice.

## Otimizações da API

- `GET /api/v1/dashboard/resumo` devolve KPIs, alertas, distribuição por categoria, gráfico de saldo e últimas movimentações numa resposta só. O frontend fazia uma chamada por bloco.
- Nesse endpoint as entradas e saídas são contadas no banco (`COUNT ... GROUP BY tipo`) e só as 12 últimas movimentações são carregadas. As categorias vêm com os produtos por `joinedload`, sem uma consulta por categoria.
- Listagens com paginação (`skip`, `limit` até 500) e filtros: produtos por categoria, controlado, em alerta e busca por nome; movimentações por produto e tipo.
- Erros com código coerente: 404 para registro inexistente, 400 para regra de negócio, 409 para conflito (exclusão com histórico, violação de chave), 422 para dado inválido (Pydantic).

## LLM

Código em [`app/services/ia_service.py`](../app/services/ia_service.py).

- Modelo: Google Gemini `gemini-2.5-flash`, pela API REST (`generateContent`), com resposta em JSON (`responseMimeType: application/json`) e temperatura baixa (0,1 na leitura de relato, 0,2 no parecer).
- Uso 1, leitura de relato cirúrgico (`POST /api/v1/ia/interpretar-relato`): a equipe escreve em texto livre o que foi usado. O Gemini recebe o relato e o catálogo (id, nome, se é controlado, dose máxima, saldo) e devolve os itens com quantidade e dose. Cada item passa pelas mesmas travas da movimentação manual. Só se todos passarem, e se o usuário marcou a baixa automática, as saídas são gravadas.
- Uso 2, parecer de compras (`POST /api/v1/ia/relatorio-inteligente`): o Gemini recebe os KPIs e os itens em alerta (nome, saldo, mínimo, preço) e devolve diagnóstico, lista de compras e comentário sobre os controlados.
- A resposta do Gemini não é usada direto: produto que não existe no catálogo, quantidade inválida ou JSON fora do formato são descartados, e a decisão de bloquear ou não é sempre do backend.
- Sem `GEMINI_API_KEY`, ou se a chamada falhar, entra um extrator por regras (expressões regulares contra o catálogo). Ele serve para a aplicação não parar, mas não é IA e só entende frases parecidas com os exemplos.

Dados enviados e cuidados:

- CPF é mascarado antes de ir para o Gemini e antes de gravar no histórico.
- O nome do paciente é identificado no servidor e trocado por `[PACIENTE]` no texto enviado ao Gemini.
- A chave vai no header `x-goog-api-key`, não na URL, e só existe como variável de ambiente no servidor. Não há rota para alterá-la.

Limitações:

- Nome comercial diferente do cadastrado, abreviação ou erro de digitação podem fazer o item não ser encontrado.
- O Gemini pode errar quantidade ou dose. Por isso as travas rodam depois e a baixa automática é opcional.
- O nome do paciente ainda fica gravado nas movimentações, que podem ser lidas por qualquer um enquanto não houver login.
