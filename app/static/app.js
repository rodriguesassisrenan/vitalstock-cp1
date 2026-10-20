const API_BASE = '/api/v1';

let chartEstoqueInstance = null;
let chartCategoriasInstance = null;
let cachedProdutos = [];
let cachedCategorias = [];

function showFeedback(message, type = 'success') {
  const banner = document.getElementById('feedback-banner');
  const text = document.getElementById('feedback-text');
  banner.className = type;
  text.textContent = message;
  banner.style.display = 'flex';
  banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideFeedback() {
  const banner = document.getElementById('feedback-banner');
  banner.className = '';
  banner.style.display = 'none';
}

function switchTab(tabId, breadcrumbText, btnEl) {
  document.querySelectorAll('.tab-section').forEach((sec) => sec.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach((btn) => btn.classList.remove('active'));
  document.getElementById(`tab-${tabId}`).classList.add('active');
  if (btnEl) btnEl.classList.add('active');
  if (breadcrumbText) {
    document.getElementById('breadcrumb-current').textContent = breadcrumbText;
  }

  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'estoque') {
    loadCategorias();
    loadProdutos();
  }
  if (tabId === 'movimentacoes') {
    loadProdutosSelect();
    loadMovimentacoes();
  }
  if (tabId === 'ia') {
    verificarStatusChaveGemini();
    loadHistoricoIA();
  }
}

function formatCurrency(val) {
  return Number(val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatDate(dtStr) {
  if (!dtStr) return '--';
  const d = new Date(dtStr.endsWith('Z') ? dtStr : dtStr + 'Z');
  return d.toLocaleString('pt-BR');
}

/* ==================== DASHBOARD ==================== */
async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/resumo`);
    if (!res.ok) throw new Error('Falha ao comunicar com a API do VitalStock.');
    const data = await res.json();

    document.getElementById('kpi-total-produtos').textContent = data.kpis.total_produtos;
    document.getElementById('kpi-sub-categorias').textContent = `${data.kpis.total_categorias} grupos farmacológicos ativos`;
    document.getElementById('kpi-alertas').textContent = data.kpis.itens_em_alerta_critico;
    document.getElementById('kpi-controlados').textContent = data.kpis.produtos_controlados;
    document.getElementById('kpi-valor-total').textContent = formatCurrency(data.kpis.valor_total_estoque);
    document.getElementById('kpi-sub-movs').textContent = `${data.kpis.total_movimentacoes} lançamentos (${data.kpis.total_entradas} entradas / ${data.kpis.total_saidas} saídas)`;

    const pillsList = document.getElementById('alert-pills-list');
    if (data.alertas_emergencia.length === 0) {
      pillsList.innerHTML = `<span class="pill pill-optimal"><span class="pill-dot"></span>Todos os insumos operam acima da margem de segurança cirúrgica.</span>`;
    } else {
      pillsList.innerHTML = data.alertas_emergencia
        .map(
          (p) => `
          <div class="alert-chip">
            <span class="pill pill-critical"><span class="pill-dot"></span>Crítico</span>
            <strong>${p.nome}</strong>
            <span class="mono" style="color:var(--text-secondary);">Saldo: <b>${p.saldo_atual}</b> / Mín: ${p.estoque_minimo_emergencia}</span>
          </div>`
        )
        .join('');
    }

    renderCharts(data.estoque_comparativo, data.distribuicao_categorias);

    const tbody = document.getElementById('dashboard-movs-tbody');
    tbody.innerHTML = data.ultimas_movimentacoes
      .map(
        (m) => `
        <tr>
          <td class="mono">#${m.id}</td>
          <td class="mono" style="font-size:12px;color:var(--text-secondary);">${formatDate(m.data_hora)}</td>
          <td><strong>${m.produto_nome}</strong></td>
          <td>
            <span class="pill ${m.tipo === 'entrada' ? 'pill-optimal' : 'pill-warning'}">
              <span class="pill-dot"></span>${m.tipo === 'entrada' ? 'Entrada' : 'Saída'}
            </span>
          </td>
          <td class="mono"><strong>${m.quantidade}</strong></td>
          <td class="mono">${m.crm_medico || '<span style="color:var(--text-muted)">—</span>'}</td>
          <td class="mono">${m.dose_prescrita ? m.dose_prescrita + ' mg' : '<span style="color:var(--text-muted)">—</span>'}</td>
          <td>${m.nome_paciente || m.observacao || '—'}</td>
        </tr>`
      )
      .join('');
  } catch (err) {
    showFeedback(err.message, 'error');
  }
}

function renderCharts(comparativo, distribuicao) {
  if (typeof Chart === 'undefined') return;

  const ctxEstoque = document.getElementById('chartEstoque').getContext('2d');
  if (chartEstoqueInstance) chartEstoqueInstance.destroy();

  chartEstoqueInstance = new Chart(ctxEstoque, {
    type: 'bar',
    data: {
      labels: comparativo.map((i) => (i.nome.length > 24 ? i.nome.slice(0, 24) + '…' : i.nome)),
      datasets: [
        {
          label: 'Saldo Físico Atual',
          data: comparativo.map((i) => i.saldo_atual),
          backgroundColor: comparativo.map((i) => (i.em_alerta ? '#dc2626' : '#0f766e')),
          borderRadius: 4,
          barPercentage: 0.65,
        },
        {
          label: 'Margem Mínima Cirúrgica',
          data: comparativo.map((i) => i.estoque_minimo_emergencia),
          backgroundColor: '#cbd5e1',
          borderRadius: 4,
          barPercentage: 0.65,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          align: 'end',
          labels: { color: '#475569', boxWidth: 12, font: { family: 'Inter', size: 12 } },
        },
      },
      scales: {
        x: {
          ticks: { color: '#475569', font: { family: 'Inter', size: 11 } },
          grid: { display: false },
        },
        y: {
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 11 } },
          grid: { color: '#f1f5f9' },
        },
      },
    },
  });

  const ctxCat = document.getElementById('chartCategorias').getContext('2d');
  if (chartCategoriasInstance) chartCategoriasInstance.destroy();

  chartCategoriasInstance = new Chart(ctxCat, {
    type: 'doughnut',
    data: {
      labels: distribuicao.map((c) => c.categoria),
      datasets: [
        {
          data: distribuicao.map((c) => c.valor_financeiro),
          backgroundColor: ['#0f766e', '#0369a1', '#334155', '#d97706', '#4f46e5', '#059669'],
          borderWidth: 2,
          borderColor: '#ffffff',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '64%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#475569', boxWidth: 10, padding: 14, font: { family: 'Inter', size: 11.5 } },
        },
      },
    },
  });
}

/* ==================== CATEGORIAS & PRODUTOS ==================== */
async function loadCategorias() {
  const res = await fetch(`${API_BASE}/categorias/`);
  cachedCategorias = await res.json();

  const selectProd = document.getElementById('prod-categoria');
  const selectFiltro = document.getElementById('filtro-categoria');
  const tagsDiv = document.getElementById('categorias-tags');

  selectProd.innerHTML = cachedCategorias.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
  const currentFilter = selectFiltro.value;
  selectFiltro.innerHTML =
    `<option value="">Todos os Grupos</option>` +
    cachedCategorias.map((c) => `<option value="${c.id}">${c.nome}</option>`).join('');
  selectFiltro.value = currentFilter;

  tagsDiv.innerHTML = cachedCategorias
    .map((c) => `<span class="pill pill-neutral" title="${c.descricao || ''}">Cód. ${c.id} — ${c.nome}</span>`)
    .join('');
}

async function handleCreateCategoria(e) {
  e.preventDefault();
  const payload = {
    nome: document.getElementById('cat-nome').value.trim(),
    descricao: document.getElementById('cat-desc').value.trim() || null,
  };

  const res = await fetch(`${API_BASE}/categorias/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    showFeedback(data.detail || 'Não foi possível cadastrar o grupo farmacológico.', 'error');
    return;
  }
  showFeedback(`Grupo farmacológico "${data.nome}" registrado com sucesso.`);
  document.getElementById('form-categoria').reset();
  loadCategorias();
}

async function loadProdutos() {
  const busca = document.getElementById('filtro-busca').value.trim();
  const catId = document.getElementById('filtro-categoria').value;
  const ctrl = document.getElementById('filtro-controlado').value;
  const alerta = document.getElementById('filtro-alerta').checked;

  const params = new URLSearchParams();
  if (busca) params.append('busca', busca);
  if (catId) params.append('categoria_id', catId);
  if (ctrl !== '') params.append('controlado', ctrl);
  if (alerta) params.append('apenas_alerta', 'true');

  const res = await fetch(`${API_BASE}/produtos/?${params.toString()}`);
  cachedProdutos = await res.json();

  const tbody = document.getElementById('produtos-tbody');
  tbody.innerHTML = cachedProdutos
    .map((p) => {
      const emRisco = p.saldo_atual <= p.estoque_minimo_emergencia;
      const pct = p.estoque_minimo_emergencia > 0
        ? Math.min(100, Math.round((p.saldo_atual / (p.estoque_minimo_emergencia * 2)) * 100))
        : 100;
      const barColor = emRisco ? '#dc2626' : '#0f766e';

      return `
      <tr>
        <td class="mono">#${p.id}</td>
        <td><strong>${p.nome}</strong></td>
        <td class="mono" style="font-size:12px;color:var(--text-secondary);">${p.lote || 'PADRÃO'} · ${p.unidade_medida || 'un'}</td>
        <td class="mono">${formatCurrency(p.preco)}</td>
        <td>
          <div class="stock-cell">
            <div style="display:flex;justify-content:space-between;font-size:12px;" class="mono">
              <strong style="color:${emRisco ? 'var(--status-critical-text)' : 'var(--text-primary)'}">${p.saldo_atual} un.</strong>
              <span style="color:var(--text-muted)">mín. ${p.estoque_minimo_emergencia}</span>
            </div>
            <div class="stock-bar-track">
              <div class="stock-bar-fill" style="width:${pct}%;background-color:${barColor};"></div>
            </div>
          </div>
        </td>
        <td>${
          p.controlado
            ? '<span class="pill pill-controlled">Portaria 344</span>'
            : '<span class="pill pill-neutral">Livre</span>'
        }</td>
        <td class="mono">${p.dose_maxima ? p.dose_maxima + ' mg' : '<span style="color:var(--text-muted)">Não aplicável</span>'}</td>
        <td>${
          emRisco
            ? '<span class="pill pill-critical"><span class="pill-dot"></span>Reposição Crítica</span>'
            : '<span class="pill pill-optimal"><span class="pill-dot"></span>Estoque Regular</span>'
        }</td>
        <td>
          <button class="btn btn-danger-ghost" onclick="handleDeleteProduto(${p.id}, '${p.nome.replace(/'/g, "\\'")}')">Remover</button>
        </td>
      </tr>`;
    })
    .join('');
}

async function handleCreateProduto(e) {
  e.preventDefault();
  const doseVal = document.getElementById('prod-dose-max').value;
  const payload = {
    nome: document.getElementById('prod-nome').value.trim(),
    categoria_id: Number(document.getElementById('prod-categoria').value),
    preco: Number(document.getElementById('prod-preco').value),
    saldo_inicial: Number(document.getElementById('prod-saldo-inicial').value),
    estoque_minimo_emergencia: Number(document.getElementById('prod-minimo').value),
    dose_maxima: doseVal ? Number(doseVal) : null,
    unidade_medida: document.getElementById('prod-unidade').value.trim() || 'ampola',
    controlado: document.getElementById('prod-controlado').value === 'true',
  };

  const res = await fetch(`${API_BASE}/produtos/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    showFeedback(data.detail || 'Erro ao cadastrar item farmacêutico.', 'error');
    return;
  }
  showFeedback(`Item "${data.nome}" incluído no catálogo com saldo inicial de ${data.saldo_atual} unidades.`);
  document.getElementById('form-produto').reset();
  loadProdutos();
}

async function handleDeleteProduto(id, nome) {
  const res = await fetch(`${API_BASE}/produtos/${id}`, { method: 'DELETE' });
  if (res.status === 204) {
    showFeedback(`Item "${nome}" removido do catálogo.`);
    loadProdutos();
  } else {
    showFeedback('Não foi possível remover o item selecionado.', 'error');
  }
}

/* ==================== MOVIMENTAÇÕES & TRAVAS ==================== */
async function loadProdutosSelect() {
  const res = await fetch(`${API_BASE}/produtos/`);
  cachedProdutos = await res.json();
  const sel = document.getElementById('mov-produto');
  sel.innerHTML = cachedProdutos
    .map(
      (p) =>
        `<option value="${p.id}">Cód. ${p.id} — ${p.nome} (Saldo: ${p.saldo_atual} | ${
          p.controlado ? 'Portaria 344' : 'Comum'
        }${p.dose_maxima ? ' | Teto: ' + p.dose_maxima + 'mg' : ''})</option>`
    )
    .join('');
}

async function loadMovimentacoes() {
  const res = await fetch(`${API_BASE}/movimentacoes/`);
  const movs = await res.json();
  const tbody = document.getElementById('movimentacoes-tbody');
  tbody.innerHTML = movs
    .map(
      (m) => `
      <tr>
        <td class="mono">#${m.id}</td>
        <td class="mono" style="font-size:12px;color:var(--text-secondary);">${formatDate(m.data_hora)}</td>
        <td class="mono">Item #${m.produto_id}</td>
        <td>
          <span class="pill ${m.tipo === 'entrada' ? 'pill-optimal' : 'pill-warning'}">
            <span class="pill-dot"></span>${m.tipo === 'entrada' ? 'Entrada' : 'Saída'}
          </span>
        </td>
        <td class="mono"><strong>${m.quantidade}</strong></td>
        <td class="mono">${m.crm_medico || '—'}</td>
        <td class="mono">${m.dose_prescrita ? m.dose_prescrita + ' mg' : '—'}</td>
        <td>${m.nome_paciente || m.observacao || '—'}</td>
      </tr>`
    )
    .join('');
}

function preencherCenarioMov(cenario) {
  const controladoProd = cachedProdutos.find((p) => p.controlado && p.dose_maxima) || cachedProdutos[0];
  if (!controladoProd) return;

  document.getElementById('mov-produto').value = controladoProd.id;
  document.getElementById('mov-tipo').value = 'saida';

  if (cenario === 'sucesso') {
    document.getElementById('mov-qtd').value = 1;
    document.getElementById('mov-crm').value = 'CRM-SP 145890';
    document.getElementById('mov-dose').value = controladoProd.dose_maxima ? +(controladoProd.dose_maxima * 0.5).toFixed(2) : 0.05;
    document.getElementById('mov-paciente').value = 'Carlos Eduardo (Sala Cirúrgica 01)';
  } else if (cenario === 'erro_anvisa') {
    document.getElementById('mov-qtd').value = 1;
    document.getElementById('mov-crm').value = '';
    document.getElementById('mov-dose').value = controladoProd.dose_maxima ? +(controladoProd.dose_maxima * 0.5).toFixed(2) : 0.05;
    document.getElementById('mov-paciente').value = 'Paciente Sem Prescritor Informado';
  } else if (cenario === 'erro_dose') {
    document.getElementById('mov-qtd').value = 1;
    document.getElementById('mov-crm').value = 'CRM-SP 145890';
    document.getElementById('mov-dose').value = controladoProd.dose_maxima ? +(controladoProd.dose_maxima * 5).toFixed(2) : 999;
    document.getElementById('mov-paciente').value = 'Simulação de Sobredose Posológica';
  } else if (cenario === 'erro_saldo') {
    document.getElementById('mov-qtd').value = controladoProd.saldo_atual + 500;
    document.getElementById('mov-crm').value = 'CRM-SP 145890';
    document.getElementById('mov-dose').value = controladoProd.dose_maxima ? +(controladoProd.dose_maxima * 0.5).toFixed(2) : 0.05;
    document.getElementById('mov-paciente').value = 'Simulação de Retirada Acima do Saldo';
  }
}

async function handleCreateMovimentacao(e) {
  e.preventDefault();
  const crm = document.getElementById('mov-crm').value.trim();
  const dose = document.getElementById('mov-dose').value;
  const pac = document.getElementById('mov-paciente').value.trim();

  const payload = {
    produto_id: Number(document.getElementById('mov-produto').value),
    tipo: document.getElementById('mov-tipo').value,
    quantidade: Number(document.getElementById('mov-qtd').value),
    crm_medico: crm || null,
    dose_prescrita: dose ? Number(dose) : null,
    nome_paciente: pac || null,
  };

  const res = await fetch(`${API_BASE}/movimentacoes/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    showFeedback(`Operação Bloqueada pela Regra Clínica: ${data.detail}`, 'error');
    return;
  }
  showFeedback(`Movimentação #${data.id} (${data.tipo.toUpperCase()}) registrada e auditada com sucesso.`);
  loadProdutosSelect();
  loadMovimentacoes();
}

/* ==================== AUTOMAÇÃO CLÍNICA (LLM) ==================== */
async function verificarStatusChaveGemini() {
  try {
    const res = await fetch(`${API_BASE}/ia/status-chave`);
    const data = await res.json();
    const lbl = document.getElementById('status-chave-label');
    if (data.gemini_api_ativa) {
      lbl.innerHTML = `<span class="pill pill-optimal"><span class="pill-dot"></span>Conectado à API Google Gemini (${data.modelo_configurado})</span>`;
    } else {
      lbl.innerHTML = `<span class="pill pill-controlled">Modo Local Ativo: ${data.modelo_configurado} (Insira uma chave Gemini ao lado caso deseje chamar a API em nuvem)</span>`;
    }
  } catch (e) {
    // ignore
  }
}

async function salvarChaveGemini() {
  const key = document.getElementById('input-gemini-key').value.trim();
  const res = await fetch(`${API_BASE}/ia/configurar-chave`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: key }),
  });
  const data = await res.json();
  showFeedback(data.mensagem, 'success');
  document.getElementById('input-gemini-key').value = '';
  verificarStatusChaveGemini();
}

function preencherRelatoIA(tipo) {
  const txt = document.getElementById('ia-relato-texto');
  if (tipo === 'aprovado') {
    txt.value =
      'Procedimento cirúrgico do paciente Marcos Paulo finalizado pelo Dr. CRM-SP 55412. Utilizamos 1 ampola de Fentanil com dose de 0.05mg e 2 frascos de Propofol com dose de 120mg.';
  } else if (tipo === 'overdose') {
    txt.value =
      'Cirurgia de emergência paciente Fernanda Lima pelo médico CRM-SP 88210. Foi prescrito 1 ampola de Fentanil na dose de 2.5mg para analgesia pós-operatória.';
  } else if (tipo === 'sem_crm') {
    txt.value =
      'Paciente Lucas Oliveira (CPF 123.456.789-00) recebeu 2 ampolas de Morfina na dose de 5mg e 1 Propofol dose 100mg na enfermaria cirúrgica sem assinatura médica.';
  }
}

async function handleRelatoIA(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-processar-relato');
  btn.textContent = 'Processando relato...';
  btn.disabled = true;

  const payload = {
    relato_texto: document.getElementById('ia-relato-texto').value.trim(),
    executar_baixa_automatica: document.getElementById('ia-executar-baixa').checked,
  };

  try {
    const res = await fetch(`${API_BASE}/ia/interpretar-relato`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    const box = document.getElementById('ia-relato-resultado');
    box.style.display = 'block';

    const pillClass =
      data.status_geral === 'APROVADO'
        ? 'pill-optimal'
        : data.status_geral.includes('BLOQUEADO')
        ? 'pill-critical'
        : 'pill-warning';

    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
        <span class="pill ${pillClass}"><span class="pill-dot"></span>${data.status_geral}</span>
        <span class="mono" style="font-size:11.5px;color:var(--text-muted);">${data.modelo_utilizado}</span>
      </div>
      <p style="font-size:13px;margin-bottom:10px;color:var(--text-primary);"><strong>Síntese da Validação:</strong> ${data.resumo_clinico_ia}</p>
      <div style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border-light);">
        <strong>Prescritor:</strong> <span class="mono">${data.crm_identificado || 'Não localizado'}</span> &nbsp;|&nbsp;
        <strong>Paciente:</strong> ${data.paciente_identificado || 'Não especificado'} &nbsp;|&nbsp;
        <strong>Baixas Efetivadas:</strong> <span class="mono">${data.baixas_realizadas}</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        ${data.itens_identificados
          .map(
            (it) => `
          <div style="padding:10px 12px;border-radius:6px;background:#ffffff;border:1px solid var(--border-light);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <strong>${it.produto_nome} — <span class="mono">Qtd: ${it.quantidade} | Dose: ${
              it.dose_prescrita_mg !== null ? it.dose_prescrita_mg + ' mg' : 'N/A'
            }</span></strong>
              <span class="pill ${it.status_validacao === 'APROVADO' ? 'pill-optimal' : 'pill-critical'}">
                <span class="pill-dot"></span>${it.status_validacao}
              </span>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">${it.mensagem_seguranca}</div>
          </div>`
          )
          .join('')}
      </div>
    `;

    loadHistoricoIA();
  } catch (err) {
    showFeedback('Erro ao processar relato cirúrgico.', 'error');
  } finally {
    btn.textContent = 'Processar Relato e Validar Regras';
    btn.disabled = false;
  }
}

async function handleGerarRelatorioIA() {
  const btn = document.getElementById('btn-relatorio-ia');
  btn.textContent = 'Processando...';
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/ia/relatorio-inteligente`, { method: 'POST' });
    const data = await res.json();
    const box = document.getElementById('ia-relatorio-resultado');

    const pillClass =
      data.nivel_risco_hospitalar === 'CRITICO'
        ? 'pill-critical'
        : data.nivel_risco_hospitalar === 'MODERADO'
        ? 'pill-warning'
        : 'pill-optimal';

    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
        <span class="pill ${pillClass}"><span class="pill-dot"></span>RISCO OPERACIONAL: ${data.nivel_risco_hospitalar}</span>
        <span class="mono" style="font-size:11.5px;color:var(--text-muted);">${data.modelo_utilizado}</span>
      </div>
      <p style="font-size:13px;margin-bottom:12px;color:var(--text-primary);"><strong>Diagnóstico da Farmácia Hospitalar:</strong><br/>${data.diagnostico_executivo}</p>
      <div style="margin-bottom:12px;">
        <strong style="font-size:12.5px;color:var(--text-primary);">Plano Prioritário de Ressuprimento:</strong>
        <ul style="margin-top:6px;padding-left:18px;font-size:12.5px;color:var(--text-secondary);">
          ${data.recomendacoes_compras.map((r) => `<li style="margin-bottom:4px;">${r}</li>`).join('')}
        </ul>
      </div>
      <div style="font-size:12px;color:var(--clinical-blue);padding:10px 12px;background:var(--clinical-blue-soft);border:1px solid var(--clinical-blue-border);border-radius:6px;">
        <strong>Auditoria Portaria 344/98 (ANVISA):</strong> ${data.analise_seguranca_anvisa}
      </div>
    `;
    loadHistoricoIA();
  } finally {
    btn.textContent = 'Emitir Parecer de Estoque';
    btn.disabled = false;
  }
}

async function loadHistoricoIA() {
  const res = await fetch(`${API_BASE}/ia/historico`);
  const list = await res.json();
  const tbody = document.getElementById('ia-historico-tbody');
  tbody.innerHTML = list
    .map(
      (h) => `
      <tr>
        <td class="mono">#${h.id}</td>
        <td class="mono" style="font-size:12px;color:var(--text-secondary);">${formatDate(h.data_hora)}</td>
        <td><span class="pill pill-neutral">${h.tipo_analise}</span></td>
        <td style="max-width:280px;font-size:12.5px;">${h.entrada_usuario}</td>
        <td style="max-width:300px;font-size:12.5px;color:var(--text-secondary);">${h.resposta_resumo}</td>
        <td class="mono" style="font-size:11.5px;">${h.modelo_utilizado}</td>
        <td>
          <span class="pill ${
            h.status_seguranca.includes('BLOQUEADO') || h.status_seguranca.includes('CRITICO')
              ? 'pill-critical'
              : 'pill-optimal'
          }">
            <span class="pill-dot"></span>${h.status_seguranca}
          </span>
        </td>
      </tr>`
    )
    .join('');
}

window.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
});
