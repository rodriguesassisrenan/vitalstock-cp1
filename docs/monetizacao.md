# 💰 Proposta de Monetização e Sustentabilidade do Negócio — VitalStock (CP3)

Este documento apresenta o plano de negócio, modelo de receita, precificação, estrutura de custos operacionais e análise de viabilidade financeira para a solução **VitalStock Hospital ERP & AI**.

---

## 1. Público-Alvo e Problema de Negócio Resolvido

### 🏥 Público-Alvo (Mercado B2B Healthtech)
1. **Hospitais de Pequeno e Médio Porte (20 a 150 leitos):** Instituições que sofrem com perdas financeiras por descontrole de farmácia satélite e não possuem orçamento para ERPs hospitalares legados milionários (como SAP ou Tasy completo).
2. **Clínicas Cirúrgicas Ambulatoriais, Day Hospitals e Clínicas Oncológicas:** Centros que manipulam diariamente medicamentos de alto custo e controlados pela Portaria 344/98 da ANVISA (Fentanil, Propofol, Morfina, Quimioterápicos).
3. **Redes de Saúde Municipais /UPAs Cirúrgicas:** Unidades que exigem auditoria rigorosa e prevenção de desabastecimento de insumos vitais.

### 🎯 Problema de Negócio e Valor Entregue
- **Cancelamento de Cirurgias por Ruptura de Estoque:** Cada sala cirúrgica parada por falta de um anestésico ou fio de sutura gera um prejuízo médio de **R$ 8.000 a R$ 25.000 por procedimento suspenso**, além do risco de óbito e processos judiciais.
- **Desperdício e Desvio de Medicamentos Controlados:** Estudos hospitalares apontam perdas de até **15% a 20%** do estoque por falhas de apontamento manual pós-cirurgia.
- **Mitigação de Passivo Jurídico e Erro Médico:** As travas nativas de **Dose Máxima Segura (Anti-Overdose)** e **Exigência de CRM (ANVISA)**, somadas à baixa automatizada por **IA (LLM)** a partir do relato cirúrgico, reduzem drasticamente erros de dispensação e multas sanitárias.

---

## 2. Modelo de Receita Escolhido e Justificativa

O modelo de receita adotado é o **B2B SaaS (Software as a Service) por Assinatura Mensal Recorrente em Tiers + Cobrança Híbrida por Uso de IA (Pay-as-you-go excedente)**.

### Por que este modelo é o ideal?
1. **Previsibilidade de Caixa (MRR/ARR):** A assinatura mensal garante receita recorrente previsível para cobrir a infraestrutura em nuvem e manutenção contínua.
2. **Baixa Barreira de Entrada:** Ao contrário de licenças perpétuas caras, o hospital contrata como despesa operacional (OPEX), sem custo pesado de implantação local.
3. **Alinhamento de Custos de IA:** Cada plano inclui uma franquia generosa de análises de relatos cirúrgicos via LLM (Google Gemini). Hospitais com altíssimo volume cirúrgico pagam centavos adicionais por lote de 1.000 requisições extras de IA, protegendo a margem bruta da operação.

---

## 3. Tabela de Preços e Simulação de Faturamento

### Planos de Assinatura (Precificação B2B)

| Plano | Perfil Indicado | Recursos Inclusos | Mensalidade (R$) |
| :--- | :--- | :--- | :--- |
| **VitalStock Clinic** | Clínicas Cirúrgicas / Day Hospital (até 2 salas cirúrgicas) | API + Dashboard em Tempo Real + Travas ANVISA/Overdose + Até 500 baixas por IA/mês | **R$ 890,00 / mês** |
| **VitalStock Hospital Pro** | Hospitais de Pequeno/Médio Porte (até 8 salas cirúrgicas) | Tudo do Clinic + Múltiplas Farmácias Satélites + Parecer Executivo IA ilimitado + 3.000 baixas IA/mês | **R$ 1.990,00 / mês** |
| **VitalStock Enterprise** | Grandes Hospitais e Redes de Saúde | Infraestrutura dedicada, integração HL7/FHIR com prontuário eletrônico, SLA 99,9% e IA ilimitada | **R$ 4.490,00 / mês** |

*(Taxa única de Onboarding e Treinamento da Equipe de Enfermagem/Farmácia: R$ 1.500,00 por instituição).*

### 📈 Simulação de Faturamento (Cenário Simples — Meta de 12 Meses)
Considerando uma carteira inicial conservadora de **25 instituições clientes** no primeiro ano de operação:
- **12 clientes** no plano *Clinic* (12 × R$ 890,00) = **R$ 10.680,00 / mês**
- **10 clientes** no plano *Hospital Pro* (10 × R$ 1.990,00) = **R$ 19.900,00 / mês**
- **3 clientes** no plano *Enterprise* (3 × R$ 4.490,00) = **R$ 13.470,00 / mês**
- **Consumo excedente de IA / Onboarding diluído:** ~ **R$ 1.500,00 / mês**
- **Receita Recorrente Mensal (MRR Total):** **R$ 45.550,00 / mês**
- **Faturamento Bruto Anualizado (ARR):** **R$ 546.600,00 / ano**

---

## 4. Estimativa de Custos Operacionais Mensais (Para atender 25 Hospitais)

A arquitetura containerizada em Python/FastAPI e o uso do modelo **Google Gemini 2.5 Flash** proporcionam um custo operacional extremamente enxuto:

| Categoria de Custo | Especificação Técnica | Custo Mensal Estimado (R$) |
| :--- | :--- | :--- |
| **Hospedagem de Aplicação (Cloud / Containers)** | Cluster de containers Docker em produção (Render Pro / AWS ECS com Auto-Scaling e Load Balancer) | R$ 650,00 |
| **Banco de Dados Gerenciado + Backups** | PostgreSQL gerenciado em alta disponibilidade (Multi-AZ) com criptografia em repouso e backups diários | R$ 580,00 |
| **Consumo de API de LLM (Google Gemini)** | ~45.000 relatos cirúrgicos/mês (~30 milhões de tokens de entrada/saída no Gemini 2.5 Flash) | R$ 320,00 |
| **Observabilidade, Segurança e Domínio/SSL** | Monitoramento de logs, WAF, certificados TLS e auditoria LGPD | R$ 250,00 |
| **Manutenção, Suporte Técnico N2 e Evolução** | Equipe enxuta de sustentação, plantão de suporte hospitalar e atualizações regulatórias ANVISA | R$ 5.200,00 |
| **Impostos sobre Faturamento (Simples Nacional ~8,5%)** | Tributação sobre emissão de NFS-e de licenciamento SaaS | R$ 3.871,75 |
| **TOTAL DE CUSTOS E DESPESAS MENSAIS** | — | **R$ 10.871,75 / mês** |

---

## 5. Análise de Viabilidade e Premissas Adotadas

- **Resultado Operacional Líquido (Lucro Mensal no cenário de 25 clientes):**
  $$\text{Lucro Líquido} = \text{R\$ } 45.550,00 - \text{R\$ } 10.871,75 = \mathbf{\text{R\$ } 34.678,25 / \text{mês}}$$
- **Margem Líquida Operacional:** **76,1%** (Margem Bruta de infraestrutura + IA superior a **96%**, típica de SaaS B2B verticalizado).
- **Ponto de Equilíbrio (Break-even Point):** Com apenas **4 hospitais no plano Hospital Pro** (R$ 7.960/mês), toda a infraestrutura técnica, banco de dados, consumo de IA e suporte básico já se pagam integralmente.
- **ROI para o Cliente Hospitalar:** Ao evitar o cancelamento de **apenas 1 cirurgia por ano** (economia de ~R$ 15.000) ou impedir **1 erro grave de dosagem medicamentosa**, o hospital já recupera integralmente o investimento anual na assinatura do VitalStock.
