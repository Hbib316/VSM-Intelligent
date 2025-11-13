// static/js/main.js
let steps = []; // array of {name, cycle_time, wait_time, cost, value_added, depends_on}
let chart = null;

// DOM refs
const stepsBody = document.getElementById("stepsBody");
const addStepBtn = document.getElementById("addStepBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const clearStepsBtn = document.getElementById("clearStepsBtn");
const sendChatBtn = document.getElementById("sendChat");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

// events
addStepBtn.addEventListener("click", () => addStepRow());
analyzeBtn.addEventListener("click", analyzeProcess);
clearStepsBtn.addEventListener("click", () => {
  steps = []; renderSteps(); document.getElementById('processInfo').classList.add('hidden');
});
sendChatBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keypress", handleChatKey);

// initial
renderSteps();

// functions
function addStepRow(prefill = {}) {
  // append to steps array with defaults
  const defaultStep = {
    name: prefill.name || `Step ${steps.length + 1}`,
    cycle_time: prefill.cycle_time || 1.0,
    wait_time: prefill.wait_time || 0,
    cost: prefill.cost || 100,
    value_added: !!prefill.value_added,
    depends_on: prefill.depends_on || []
  };
  steps.push(defaultStep);
  renderSteps();
}

function removeStep(index) {
  steps.splice(index, 1);
  renderSteps();
}

function renderSteps() {
  stepsBody.innerHTML = "";
  if (steps.length === 0) {
    stepsBody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px;color:#999">Ajoutez des étapes pour commencer</td></tr>`;
    return;
  }
  steps.forEach((s, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input class="txt name" data-index="${i}" value="${escapeHtml(s.name)}" /></td>
      <td><input type="number" step="0.1" class="num cycle" data-index="${i}" value="${s.cycle_time}" /></td>
      <td><input type="number" step="1" class="num cost" data-index="${i}" value="${s.cost}" /></td>
      <td style="text-align:center"><input type="checkbox" class="chk va" data-index="${i}" ${s.value_added ? "checked":""}></td>
      <td><input class="txt deps" data-index="${i}" placeholder="Ex: Soudure,Peinture" value="${escapeHtml((s.depends_on||[]).join(','))}"></td>
      <td><button class="btn btn-primary" onclick="removeStep(${i})">🗑️</button></td>
    `;
    stepsBody.appendChild(tr);
  });

  // add listeners to inputs to update steps array on change
  document.querySelectorAll(".name").forEach(inp => inp.onchange = handleStepInput);
  document.querySelectorAll(".cycle").forEach(inp => inp.onchange = handleStepInput);
  document.querySelectorAll(".cost").forEach(inp => inp.onchange = handleStepInput);
  document.querySelectorAll(".va").forEach(inp => inp.onchange = handleStepInput);
  document.querySelectorAll(".deps").forEach(inp => inp.onchange = handleStepInput);
  document.getElementById('processInfo').classList.remove('hidden');
  document.getElementById('processName').textContent = "Processus dynamique";
}

function handleStepInput(e) {
  const idx = parseInt(e.target.dataset.index, 10);
  if (isNaN(idx) || idx < 0 || idx >= steps.length) return;
  const row = e.target;
  // read current row values
  const root = row.closest('tr');
  const name = root.querySelector(".name").value.trim();
  const cycle = parseFloat(root.querySelector(".cycle").value) || 0;
  const cost = parseFloat(root.querySelector(".cost").value) || 0;
  const va = root.querySelector(".va").checked;
  const depsRaw = root.querySelector(".deps").value.trim();
  const deps = depsRaw.length ? depsRaw.split(",").map(s=>s.trim()).filter(Boolean) : [];
  steps[idx].name = name || `Step ${idx+1}`;
  steps[idx].cycle_time = cycle;
  steps[idx].cost = cost;
  steps[idx].value_added = !!va;
  steps[idx].depends_on = deps;
}

async function analyzeProcess() {
  // make sure we snapshot latest inputs
  document.querySelectorAll(".name").forEach(n => n.dispatchEvent(new Event('change')));
  if (steps.length === 0) return alert("Ajoutez des étapes avant l'analyse.");

  // build payload
  const payload = {
    process_name: "Processus dynamique",
    steps: steps.map(s => ({
      name: s.name,
      cycle_time: Number(s.cycle_time),
      cost: Number(s.cost),
      value_added: !!s.value_added,
      depends_on: s.depends_on || []
    }))
  };

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.error) {
      alert("Erreur d'analyse: " + data.error);
      return;
    }
    showResults(data);
    addBotMessage(`📊 Analyse terminée. Lead time: ${data.summary.lead_time} h, VA ratio: ${data.summary.va_ratio}%`);
    // update local steps with returned scheduling info
    if (Array.isArray(data.steps)) {
      // map back wait_time etc.
      data.steps.forEach((s, idx) => {
        if (steps[idx]) {
          steps[idx].wait_time = s.start_time || s.wait_time || s.wait;
        }
      });
      renderSteps();
    }
  } catch (err) {
    alert("Erreur réseau: " + err.message);
  }
}

function showResults(data) {
  document.getElementById("resultsSection").classList.remove("hidden");
  document.getElementById("leadTime").textContent = data.summary.lead_time;
  document.getElementById("vaRatio").textContent = data.summary.va_ratio;
  document.getElementById("totalWait").textContent = data.summary.total_wait_time || 0;
  // compute total cost
  const totalCost = (data.steps || []).reduce((s,x)=> s + (x.cost || 0), 0);
  document.getElementById("totalCost").textContent = '$' + totalCost;

  // Chart
  const labels = data.timeline.map(t => t.name);
  const waitData = data.timeline.map(t => t.wait);
  const cycleData = data.timeline.map(t => t.cycle);

  const ctx = document.getElementById("vsmChart").getContext("2d");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Temps Attente (h)', data: waitData, backgroundColor: '#ef4444' },
        { label: 'Temps Cycle (h)', data: cycleData, backgroundColor: '#10b981' }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { stacked: false }, y: { stacked: false } }
    }
  });

  // report & alerts
  document.getElementById("aiReport").textContent = data.ai_report || "";
  const rec = document.getElementById("recommendationsList");
  rec.innerHTML = "";
  (data.alerts || []).forEach(a => {
    const li = document.createElement("li"); li.textContent = a; rec.appendChild(li);
  });
}

// Chatbot helpers
function addUserMessage(text) {
  const d = document.createElement('div'); d.className = 'message user';
  d.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(d); chatMessages.scrollTop = chatMessages.scrollHeight;
}
function addBotMessage(text) {
  const d = document.createElement('div'); d.className = 'message bot';
  d.innerHTML = `<div class="message-content">${text}</div>`;
  chatMessages.appendChild(d); chatMessages.scrollTop = chatMessages.scrollHeight;
}
async function sendChat() {
  const text = chatInput.value.trim();
  if (!text) return;
  addUserMessage(text);
  chatInput.value = '';
  try {
    const res = await fetch('/api/chat', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    addBotMessage(data.response);
  } catch (e) {
    addBotMessage("Erreur chatbot: " + e.message);
  }
}
function handleChatKey(e) {
  if (e.key === 'Enter') sendChat();
}

// utility
function escapeHtml(str) {
  return ('' + str).replace(/[&<>"']/g, function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];});
}
