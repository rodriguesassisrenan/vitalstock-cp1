# Evidências

Deploy na AWS em 20/10/2026, instância `i-010e22ea03b4e36a1` (t3.micro, us-east-1), endereço http://34.204.49.93:8000/.

| Arquivo | O que mostra |
| --- | --- |
| `01_deploy_cloudshell.png` | saída do `aws/cloudshell_criar_ec2.sh`: instância criada e `/health` respondendo |
| `02_ec2_running.png` | instância no console da EC2, executando, 3/3 verificações |
| `03_health.png` | `/health` aberto no navegador, com o Gemini ativo |
| `04_swagger.png` | Swagger publicado em `/docs` |
| `05_dashboard.png` | dashboard no deploy, com os dois itens em alerta |
| `06_trava_dose.png` | saída de Fentanil com 0,5 mg bloqueada (máximo 0,1 mg) |
| `07_ia_gemini.png` | relato cirúrgico lido pelo Gemini, aprovado nas travas, 2 baixas e registro no histórico |
| `relatorio_pytest.txt` | `pytest -v` com os 17 testes passando |
