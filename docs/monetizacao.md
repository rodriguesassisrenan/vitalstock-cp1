# Monetização

## Público e problema

Clientes: clínicas cirúrgicas e day hospitals (1 a 3 salas) e hospitais de 20 a 150 leitos. São lugares que usam opioides e anestésicos todo dia, precisam cumprir a Portaria 344/98 e normalmente controlam estoque em planilha ou num módulo genérico do ERP.

O que o VitalStock resolve para eles:

- Cirurgia suspensa por falta de insumo. Uma sala parada custa caro (honorários, sala, remarcação); nossa estimativa é de alguns milhares de reais por procedimento, e o alerta de estoque mínimo ataca isso direto.
- Baixa de estoque esquecida depois da cirurgia, que deixa o saldo errado. A leitura do relato pela IA reduz o trabalho de lançar item por item.
- Saída de controlado sem prescritor e dose fora do padrão, que viram problema em auditoria.

## Modelo de receita

Assinatura mensal (SaaS), com três planos e uma taxa de implantação. Escolhemos assinatura porque o custo do sistema é contínuo (servidor, banco, LLM, suporte) e porque hospital pequeno tem mais facilidade de aprovar uma mensalidade do que uma licença cara de uma vez.

| Plano | Para quem | Inclui | Mensalidade |
| --- | --- | --- | --- |
| Clinic | até 2 salas | estoque, dashboard, travas, 500 leituras de relato por mês | R$ 890 |
| Hospital | até 8 salas | tudo do Clinic, várias farmácias satélite, 3.000 leituras por mês | R$ 1.990 |
| Enterprise | redes e hospitais maiores | integração com prontuário, SLA, leituras sem limite | R$ 4.490 |

Implantação e treinamento: R$ 1.500 por cliente, cobrados uma vez. Leituras de relato acima da franquia são cobradas por pacote.

## Simulação com 25 clientes

| Plano | Clientes | Receita mensal |
| --- | --- | --- |
| Clinic | 12 | R$ 10.680 |
| Hospital | 10 | R$ 19.900 |
| Enterprise | 3 | R$ 13.470 |
| Excedente de IA e implantação diluída | | R$ 1.500 |
| Total | 25 | R$ 45.550 |

Receita anual: R$ 546.600.

## Custos mensais

| Item | Premissa | Custo |
| --- | --- | --- |
| Hospedagem | contêineres em nuvem com balanceador (AWS ECS ou similar) | R$ 650 |
| Banco | PostgreSQL gerenciado com backup diário | R$ 580 |
| Gemini | cerca de 45 mil relatos por mês no gemini-2.5-flash | R$ 320 |
| Monitoramento, domínio, certificado | | R$ 250 |
| Equipe de suporte e manutenção | 2 pessoas em meio período ou 1 em tempo integral com encargos | R$ 12.000 |
| Impostos | Simples Nacional, cerca de 8,5% da receita | R$ 3.872 |
| Total | | R$ 17.672 |

## Viabilidade

- Resultado mensal com 25 clientes: R$ 45.550 − R$ 17.672 = R$ 27.878 (margem de cerca de 61%).
- Os custos fixos sem imposto somam R$ 13.800. Descontando os 8,5% de imposto, o ponto de equilíbrio fica em torno de R$ 15.100 de receita mensal, ou seja, uns 8 clientes no plano Hospital.
- Para o cliente: evitar uma cirurgia suspensa por ano já paga boa parte da assinatura anual do plano Clinic (R$ 10.680).

Premissas e riscos:

- 25 clientes no primeiro ano é uma meta otimista para um time pequeno; venda para hospital é lenta e passa por TI e farmácia.
- O custo do Gemini foi estimado pela tabela de preço por token do modelo e pode mudar.
- O valor de cirurgia suspensa e o ganho para o cliente são estimativas do grupo, não pesquisa de mercado.
- Para vender de verdade faltariam login, perfis de acesso e adequação à LGPD, o que aumenta o custo de desenvolvimento antes da primeira venda.
