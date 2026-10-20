import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

TEST_DB_FILE = "./test_vitalstock.db"
SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine_test = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    Base.metadata.create_all(bind=engine_test)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    engine_test.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


client = TestClient(app)


def test_01_healthcheck_e_frontend():
    """Cenário 1: Verifica disponibilidade do Healthcheck e da Interface Visual (Frontend/Dashboard)"""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_front = client.get("/")
    assert res_front.status_code == 200
    assert "VitalStock" in res_front.text


def test_02_criar_e_listar_categoria_sucesso():
    """Cenário 2 (Sucesso): Cadastro e listagem de categoria hospitalar"""
    payload = {
        "nome": "Analgésicos Opióides Teste",
        "descricao": "Medicamentos de controle especial Portaria 344/98",
    }
    res = client.post("/api/v1/categorias/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == 1
    assert data["nome"] == payload["nome"]

    res_list = client.get("/api/v1/categorias/")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_03_bloqueio_categoria_duplicada_erro():
    """Cenário 3 (Erro): Impede duplicidade de categorias com o mesmo nome"""
    payload = {"nome": "Analgésicos Opióides Teste", "descricao": "Duplicada"}
    res = client.post("/api/v1/categorias/", json=payload)
    assert res.status_code == 400
    assert "já cadastrada" in res.json()["detail"]


def test_04_criar_medicamento_controlado_com_saldo_inicial():
    """Cenário 4 (Sucesso): Cadastro de medicamento controlado com limite de dose máxima e saldo inicial"""
    payload = {
        "nome": "Fentanil Citrato Injetável 0,05mg/ml",
        "preco": 45.0,
        "categoria_id": 1,
        "controlado": True,
        "dose_maxima": 0.1,
        "estoque_minimo_emergencia": 10,
        "saldo_inicial": 15,
    }
    res = client.post("/api/v1/produtos/", json=payload)
    assert res.status_code == 201
    prod = res.json()
    assert prod["saldo_atual"] == 15
    assert prod["controlado"] is True
    assert prod["dose_maxima"] == 0.1


def test_05_trava_anvisa_saida_controlado_sem_crm_erro():
    """Cenário 5 (Erro - Regra de Negócio ANVISA): Bloqueia saída de controlado sem CRM médico"""
    payload = {
        "produto_id": 1,
        "tipo": "saida",
        "quantidade": 2,
        "crm_medico": None,
        "dose_prescrita": 0.05,
        "nome_paciente": "Paciente Teste Sem CRM",
    }
    res = client.post("/api/v1/movimentacoes/", json=payload)
    assert res.status_code == 400
    assert "ALERTA DE SEGURANÇA" in res.json()["detail"]
    assert "CRM" in res.json()["detail"]


def test_06_trava_anti_overdose_dose_letal_erro():
    """Cenário 6 (Erro - Regra Anti-Erro Médico): Bloqueia saída com dose prescrita acima da dose máxima"""
    payload = {
        "produto_id": 1,
        "tipo": "saida",
        "quantidade": 1,
        "crm_medico": "CRM-SP 123456",
        "dose_prescrita": 0.85,  # Limite máximo do Fentanil é 0.1mg!
        "nome_paciente": "Paciente Protegido Contra Overdose",
    }
    res = client.post("/api/v1/movimentacoes/", json=payload)
    assert res.status_code == 400
    assert "ALERTA FATAL EVITADO" in res.json()["detail"]


def test_07_trava_estoque_fisico_insuficiente_erro():
    """Cenário 7 (Erro - Trava de Estoque Físico): Bloqueia retirada superior ao saldo disponível"""
    payload = {
        "produto_id": 1,
        "tipo": "saida",
        "quantidade": 999,
        "crm_medico": "CRM-SP 123456",
        "dose_prescrita": 0.05,
        "nome_paciente": "Paciente Teste Saldo",
    }
    res = client.post("/api/v1/movimentacoes/", json=payload)
    assert res.status_code == 400
    assert "Saldo insuficiente" in res.json()["detail"]


def test_08_saida_valida_e_gatilho_alerta_emergencia():
    """Cenário 8 (Sucesso + Integração): Registra saída segura e dispara Alerta de Ruptura Cirúrgica"""
    payload = {
        "produto_id": 1,
        "tipo": "saida",
        "quantidade": 8,  # Saldo cai de 15 para 7 (abaixo do mínimo de emergência = 10)
        "crm_medico": "CRM-SP 123456",
        "dose_prescrita": 0.05,
        "nome_paciente": "Maria da Silva (Bloco Cirúrgico)",
    }
    res = client.post("/api/v1/movimentacoes/", json=payload)
    assert res.status_code == 201

    # Verifica que o produto entrou na lista de alertas de emergência
    res_alertas = client.get("/api/v1/produtos/alertas-emergencia")
    assert res_alertas.status_code == 200
    alertas = res_alertas.json()
    assert len(alertas) == 1
    assert alertas[0]["id"] == 1
    assert alertas[0]["saldo_atual"] == 7


def test_09_otimizacao_filtros_e_dashboard_consolidado():
    """Cenário 9 (Otimização API e Dashboard): Valida filtros avançados e endpoint consolidado do Dashboard"""
    res_filtro = client.get("/api/v1/produtos/?controlado=true&apenas_alerta=true&busca=Fentanil")
    assert res_filtro.status_code == 200
    assert len(res_filtro.json()) == 1

    res_dash = client.get("/api/v1/dashboard/resumo")
    assert res_dash.status_code == 200
    dash = res_dash.json()
    assert dash["kpis"]["total_produtos"] == 1
    assert dash["kpis"]["itens_em_alerta_critico"] == 1
    assert len(dash["ultimas_movimentacoes"]) >= 1


def test_10_ia_interpretar_relato_cirurgico_aprovado_com_baixa():
    """Cenário 10 (Integração LLM + Banco): IA interpreta relato médico válido e realiza baixa automática"""
    payload = {
        "relato_texto": (
            "Cirurgia cardíaca do paciente Carlos Alberto concluída pelo Dr. CRM-SP 55443. "
            "Utilizamos 2 ampolas de Fentanil com dose de 0.05mg."
        ),
        "executar_baixa_automatica": True,
    }
    res = client.post("/api/v1/ia/interpretar-relato", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status_geral"] == "APROVADO"
    assert data["baixas_realizadas"] == 1
    assert data["itens_identificados"][0]["status_validacao"] == "APROVADO"

    # Verifica se o saldo do Fentanil caiu de 7 para 5 no banco de dados
    res_prod = client.get("/api/v1/produtos/1")
    assert res_prod.json()["saldo_atual"] == 5


def test_11_ia_bloqueia_relato_com_overdose_e_anonimiza_cpf_lgpd():
    """Cenário 11 (Segurança IA + LGPD): IA bloqueia relato com dose letal e mascara CPF nos logs"""
    payload = {
        "relato_texto": (
            "Paciente Roberto Alves CPF 123.456.789-00 atendido pelo CRM-SP 99881. "
            "Prescrito 1 ampola de Fentanil com dose de 2.5mg."
        ),
        "executar_baixa_automatica": True,
    }
    res = client.post("/api/v1/ia/interpretar-relato", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status_geral"] == "BLOQUEADO_PELA_TRAVA_HOSPITALAR"
    assert data["baixas_realizadas"] == 0
    assert data["itens_identificados"][0]["status_validacao"] == "BLOQUEADO_DOSE_LETAL"

    # Verifica que o CPF foi anonimizado na tabela de auditoria (LGPD)
    res_hist = client.get("/api/v1/ia/historico")
    assert res_hist.status_code == 200
    ultimo_log = res_hist.json()[0]
    assert "123.456.789-00" not in ultimo_log["entrada_usuario"]
    assert "CPF PROTEGIDO LGPD" in ultimo_log["entrada_usuario"]


def test_12_ia_relatorio_executivo_risco_cirurgico():
    """Cenário 12 (Apoio à Decisão IA): Gera relatório executivo com recomendações de compra"""
    res = client.post("/api/v1/ia/relatorio-inteligente")
    assert res.status_code == 200
    data = res.json()
    assert data["nivel_risco_hospitalar"] in ("MODERADO", "CRITICO")
    assert len(data["recomendacoes_compras"]) >= 1
    assert "Fentanil" in data["diagnostico_executivo"]
