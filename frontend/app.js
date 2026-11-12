const API_BASE = 'http://localhost:8000/api';

const state = {
    currentMode: 'analyze',
    lastBrain: null,
    brainVisual: null
};

const els = {
    query: document.getElementById('query-input'),
    btnAnalyze: document.getElementById('btn-analyze'),
    btnEvaluate: document.getElementById('btn-evaluate'),
    btnCombine: document.getElementById('btn-combine'),
    btnCompare: document.getElementById('btn-compare'),
    auxSection: document.getElementById('aux-section'),
    auxFields: document.getElementById('aux-fields'),
    resultsSection: document.getElementById('results-section'),
    brainCards: document.getElementById('brain-cards'),
    resultsContent: document.getElementById('results-content'),
    rawResponse: document.getElementById('raw-response'),
    btnCopy: document.getElementById('btn-copy'),
    btnMemory: document.getElementById('btn-memory'),
    statusDot: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    modelInfo: document.getElementById('model-info')
};

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const fallback = await response.text().catch(() => '');
        throw new Error(fallback || `Request failed with status ${response.status}`);
    }
    return response.json();
}

function setStatus(status, text) {
    els.statusDot.className = 'status-dot ' + status;
    els.statusText.textContent = text;
}

function renderMarkdown(text) {
    let html = String(text)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^### (.+)$/gim, '<h3>$1</h3>')
        .replace(/^## (.+)$/gim, '<h3>$1</h3>')
        .replace(/^# (.+)$/gim, '<h2>$1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/```[\s\S]*?```/g, match => `<pre><code>${match.replace(/```/g, '')}</code></pre>`)
        .replace(/`([^`]+)`/g, '<code class="inline">$1</code>')
        .replace(/^- (.+)$/gim, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/^\d+\. (.+)$/gim, '<li>$1</li>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    const lines = html.split('\n');
    let tableBuffer = [];
    const result = [];
    for (const line of lines) {
        if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
            tableBuffer.push(line);
            continue;
        }
        if (tableBuffer.length > 0) {
            result.push(buildTable(tableBuffer));
            tableBuffer = [];
        }
        result.push(line);
    }
    if (tableBuffer.length > 0) result.push(buildTable(tableBuffer));
    return result.join('\n');
}

function buildTable(lines) {
    const headers = lines[0].split('|').filter(c => c.trim()).map(c => c.trim());
    const rows = lines.slice(2).map(l => l.split('|').filter(c => c.trim()).map(c => c.trim()));
    let html = '<table><thead><tr>';
    headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead><tbody>';
    rows.forEach(row => {
        html += '<tr>' + row.map(c => `<td>${c}</td>`).join('') + '</tr>';
    });
    return html + '</tbody></table>';
}

function confClass(c) {
    if (c >= 0.7) return 'high';
    if (c >= 0.4) return 'medium';
    return 'low';
}

function hypothesisCard(h) {
    const conf = h.confidence ?? 0;
    const verdict = h.critique?.verdict ?? '';
    const risks = (h.risks || []).slice(0, 3).map(r => `<li>${r}</li>`).join('');
    const drugs = (h.drugs || []).map(d => `<span class="tag">${d}</span>`).join('');
    const learning = h.learned_boost ? `<span class="tag learn">+${h.learned_boost} aprendizaje</span>` : '';
    return `
    <div class="card" data-id="${h.id}">
        <div class="card-head">
            <span class="card-title">${h.title}</span>
            <span class="conf-badge ${confClass(conf)}">${(conf * 100).toFixed(0)}%</span>
        </div>
        <div class="conf-bar"><div class="conf-fill ${confClass(conf)}" style="width:${(conf * 100).toFixed(0)}%"></div></div>
        <p class="card-rationale">${h.rationale || ''}</p>
        <div class="card-tags">${drugs}${learning}${verdict ? `<span class="tag verdict">${verdict}</span>` : ''}</div>
        ${risks ? `<ul class="card-risks">${risks}</ul>` : ''}
        <div class="card-feedback">
            <button class="fb-up" data-id="${h.id}">👍 Útil</button>
            <button class="fb-down" data-id="${h.id}">👎 No útil</button>
        </div>
    </div>`;
}

function renderBrain(brain) {
    els.brainCards.innerHTML = '';
    const sections = [
        ['candidates', 'Candidatos terapéuticos'],
        ['combinations', 'Hipótesis de combinación'],
        ['evaluated', 'Evaluaciones'],
        ['comparison', 'Comparativa']
    ];
    let html = '';
    for (const [key, label] of sections) {
        const items = (brain[key] || []);
        if (!items.length) continue;
        html += `<h3 class="brain-section">${label} (${items.length})</h3>`;
        html += items.map(hypothesisCard).join('');
    }
    if (!html) html = '<p class="muted">El cerebro no generó hipótesis estructuradas para esta consulta.</p>';
    els.brainCards.innerHTML = html;
    bindFeedback();
}

function bindFeedback() {
    els.brainCards.querySelectorAll('.fb-up, .fb-down').forEach(btn => {
        btn.addEventListener('click', async () => {
            const rating = btn.classList.contains('fb-up') ? 1 : -1;
            const id = btn.getAttribute('data-id');
            btn.disabled = true;
            try {
                await fetch(`${API_BASE}/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hypothesis_id: id, rating })
                });
                btn.textContent = rating > 0 ? '✓ Guardado' : '✓ Anotado';
            } catch (e) {
                btn.disabled = false;
            }
        });
    });
}

function showLoading() {
    els.resultsSection.style.display = 'block';
    els.brainCards.innerHTML = '';
    els.resultsContent.innerHTML = '<span class="loading"></span> El cerebro está razonando...';
}

function showError(message) {
    els.resultsSection.style.display = 'block';
    els.brainCards.innerHTML = '';
    els.resultsContent.innerHTML = `<div class="error-message">${message}</div>`;
}

function showResults(data) {
    els.resultsSection.style.display = 'block';
    lastBrain = data.brain;
    if (data.brain) renderBrain(data.brain);
    const response = data.llm_response || data.message || JSON.stringify(data, null, 2);
    els.resultsContent.innerHTML = renderMarkdown(response);
    els.rawResponse.textContent = JSON.stringify(data, null, 2);
}

async function checkStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        const data = await res.json();
        const stats = data.graph_stats || {};
        const total = Object.values(stats).reduce((a, b) => a + b, 0);
        if (data.llm_available) {
            setStatus('online', `Conectado | IA: ${data.active_model}`);
        } else {
            setStatus('checking', 'IA local no disponible - razonamiento simbólico activo');
        }
        const mem = data.memory_stats ? ` | Memoria: ${data.memory_stats.stored_hypotheses} hipótesis` : '';
        els.modelInfo.textContent = `Nodos: ${total}${mem}`;
    } catch (e) {
        setStatus('offline', 'Error de conexión con el servidor');
    }
}

async function sendStream(mode, payload) {
    showLoading();
    let streamBuffer = '';
    let brainRendered = false;
    try {
        const res = await fetch(`${API_BASE}/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode, ...payload })
        });
        if (!res.ok) throw new Error('Error ' + res.status);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let idx;
            while ((idx = buffer.indexOf('\n\n')) !== -1) {
                const chunk = buffer.slice(0, idx);
                buffer = buffer.slice(idx + 2);
                const evLine = chunk.split('\n').find(l => l.startsWith('event:'));
                const dataLine = chunk.split('\n').find(l => l.startsWith('data:'));
                if (!dataLine) continue;
                const event = evLine ? evLine.slice(6).trim() : 'message';
                const data = JSON.parse(dataLine.slice(5).trim());
                if (event === 'brain') {
                    if (data) renderBrain(data);
                    brainRendered = true;
                    els.resultsContent.textContent = '';
                } else if (event === 'token') {
                    streamBuffer += data.text || '';
                    els.resultsContent.textContent = streamBuffer;
                } else if (event === 'error') {
                    showError(data.detail || 'Error en streaming');
                    return;
                } else if (event === 'done') {
                    els.resultsContent.innerHTML = renderMarkdown(streamBuffer);
                }
            }
        }
        if (!brainRendered) els.resultsContent.innerHTML = renderMarkdown(streamBuffer);
    } catch (e) {
        showError(e.message);
    }
}

function setMode(mode) {
    state.currentMode = mode;
    if (!els.auxSection || !els.auxFields) return;
    els.auxSection.style.display = 'none';
    els.auxFields.innerHTML = '';
    [els.btnAnalyze, els.btnEvaluate, els.btnCombine, els.btnCompare].forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
    });
    const map = { analyze: els.btnAnalyze, evaluate: els.btnEvaluate, combine: els.btnCombine, compare: els.btnCompare };
    map[mode].classList.remove('btn-secondary');
    map[mode].classList.add('btn-primary');

    if (mode === 'evaluate') {
        els.auxSection.style.display = 'block';
        els.auxFields.innerHTML = `
            <div class="aux-field"><label>Fármaco</label><input type="text" id="aux-drug" placeholder="Ej: Lenacapavir"></div>
            <div class="aux-field"><label>Diana molecular</label><input type="text" id="aux-target" placeholder="Ej: Capsid_CA"></div>`;
    } else if (mode === 'combine') {
        els.auxSection.style.display = 'block';
        els.auxFields.innerHTML = `
            <div class="aux-field"><label>Fármacos (separados por coma)</label><input type="text" id="aux-drugs" placeholder="Ej: Lenacapavir, Dolutegravir"></div>
            <div class="aux-field"><label>Patógeno (opcional)</label><input type="text" id="aux-pathogen" placeholder="Ej: HIV"></div>`;
    } else if (mode === 'compare') {
        els.auxSection.style.display = 'block';
        els.auxFields.innerHTML = `
            <div class="aux-field"><label>Alternativas (separadas por coma)</label><input type="text" id="aux-alternatives" placeholder="Ej: Lenacapavir, Dolutegravir, Bictegravir"></div>
            <div class="aux-field"><label>Patógeno (opcional)</label><input type="text" id="aux-pathogen" placeholder="Ej: HIV"></div>`;
    }
}

function bindEvents() {
    els.btnAnalyze.addEventListener('click', () => {
        const query = els.query.value.trim();
        if (!query) return alert('Ingresa una consulta');
        sendStream('analyze', { query });
    });

    els.btnEvaluate.addEventListener('click', () => {
        const drug = document.getElementById('aux-drug')?.value.trim();
        const target = document.getElementById('aux-target')?.value.trim();
        if (!drug || !target) return alert('Completa fármaco y diana');
        sendStream('evaluate', { drug, target });
    });

    els.btnCombine.addEventListener('click', () => {
        const drugsRaw = document.getElementById('aux-drugs')?.value.trim();
        const pathogen = document.getElementById('aux-pathogen')?.value.trim();
        if (!drugsRaw) return alert('Ingresa al menos un fármaco');
        const drugs = drugsRaw.split(',').map(s => s.trim()).filter(Boolean);
        sendStream('combine', { drugs, pathogen });
    });

    els.btnCompare.addEventListener('click', () => {
        const altsRaw = document.getElementById('aux-alternatives')?.value.trim();
        const pathogen = document.getElementById('aux-pathogen')?.value.trim();
        if (!altsRaw) return alert('Ingresa al menos una alternativa');
        const alternatives = altsRaw.split(',').map(s => s.trim()).filter(Boolean);
        sendStream('compare', { alternatives, pathogen });
    });

    els.btnCopy.addEventListener('click', () => {
        const text = (els.brainCards.innerText + '\n\n' + els.resultsContent.innerText);
        navigator.clipboard.writeText(text).then(() => {
            els.btnCopy.textContent = 'Copiado';
            setTimeout(() => els.btnCopy.textContent = 'Copiar', 2000);
        });
    });

    els.btnMemory.addEventListener('click', async () => {
        try {
            const data = await fetchJson(`${API_BASE}/memory`);
            const w = data.stats?.learned_weights ?? 0;
            alert(`Memoria del cerebro:\n- Hipótesis almacenadas: ${data.stats?.stored_hypotheses ?? 0}\n- Feedback recibido: ${data.stats?.feedback_count ?? 0}\n- Pesos aprendidos: ${w}`);
        } catch (error) {
            alert('No se pudo obtener la memoria.');
        }
    });
}

function parseStreamChunk(chunk) {
    const lines = chunk.split('\n');
    const eventLine = lines.find(line => line.startsWith('event:'));
    const dataLine = lines.find(line => line.startsWith('data:'));
    if (!dataLine) return null;

    const event = eventLine ? eventLine.replace(/^event:\s*/, '').trim() : 'message';
    const rawData = dataLine.replace(/^data:\s*/, '').trim();
    if (!rawData || rawData === '[DONE]') return null;

    try {
        return { event, payload: JSON.parse(rawData) };
    } catch (error) {
        return { event, payload: rawData };
    }
}

function initAIVisuals() {
    if (!document.getElementById('particle-sphere')) return;
    state.brainVisual = new window.ParticleSphere({ canvasId: 'particle-sphere' });
}

function init() {
    bindEvents();
    setMode('analyze');
    checkStatus();
    setInterval(checkStatus, 30000);
    initAIVisuals();
}

document.addEventListener('DOMContentLoaded', init);
window.addEventListener('beforeunload', () => {
    if (state.brainVisual) {
        state.brainVisual.destroy();
    }
});
