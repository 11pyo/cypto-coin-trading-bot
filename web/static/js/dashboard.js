// ETH Auto-Trading Bot Dashboard - Client-side Logic

let socket;
try { socket = io(); } catch(e) { socket = null; }

// ===== Chart.js Setup =====
const ctx = document.getElementById("priceChart").getContext("2d");
const priceChart = new Chart(ctx, {
  type: "line",
  data: {
    labels: [],
    datasets: [{
      label: "ETH/USDT",
      data: [],
      borderColor: "#3b82f6",
      backgroundColor: "rgba(59,130,246,0.1)",
      fill: true,
      tension: 0.3,
      pointRadius: 2,
      borderWidth: 2,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: "#64748b", maxTicksLimit: 10, font: { size: 10 } }, grid: { color: "#1e293b" } },
      y: { ticks: { color: "#64748b", font: { size: 10 } }, grid: { color: "#1e293b" } }
    }
  }
});

// ===== Utility Functions =====
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setColor(id, color) {
  const el = document.getElementById(id);
  if (el) el.style.color = color;
}

function formatTime(ts) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDate(ts) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString("ko-KR") + " " + d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
}

function modeColor(mode) {
  const colors = { GOLDEN: "#eab308", RANGE: "#3b82f6", DANGER: "#ef4444", DOWNTREND: "#f97316" };
  return colors[mode] || "#64748b";
}

function modeBadgeClass(mode) {
  const cls = { GOLDEN: "badge-yellow", RANGE: "badge-blue", DANGER: "badge-red", DOWNTREND: "badge-red" };
  return cls[mode] || "badge-blue";
}

function smColor(score) {
  if (score >= 30) return "#22c55e";
  if (score >= 0) return "#3b82f6";
  if (score >= -30) return "#f59e0b";
  return "#ef4444";
}

function pnlColor(val) {
  if (val > 0) return "#22c55e";
  if (val < 0) return "#ef4444";
  return "#94a3b8";
}

// ===== Update Dashboard =====
function updateDashboard(data) {
  // Cards
  setText("card-price", "$" + (data.price || 0).toFixed(2));
  setText("card-rsi", data.rsi ? data.rsi.toFixed(1) : "-");
  setColor("card-rsi", data.rsi < 35 ? "#22c55e" : (data.rsi > 70 ? "#ef4444" : "#e2e8f0"));

  setText("card-fg", data.fear_greed !== null ? data.fear_greed : "-");
  setColor("card-fg", data.fear_greed < 30 ? "#ef4444" : (data.fear_greed > 60 ? "#22c55e" : "#f59e0b"));

  setText("card-sm", data.sm_signal || "-");
  setColor("card-sm", smColor(data.sm_score || 0));

  setText("card-trend", (data.trend_strength || 0).toFixed(0) + " " + (data.trend_direction || ""));
  setColor("card-trend", modeColor(data.mode));

  setText("card-signal", data.signal || "HOLD");
  const sigColor = data.signal === "BUY" ? "#22c55e" : (data.signal === "SELL" ? "#ef4444" : "#94a3b8");
  setColor("card-signal", sigColor);

  // Mode badge
  const mb = document.getElementById("mode-badge");
  if (mb) { mb.textContent = data.mode || "RANGE"; mb.className = "badge " + modeBadgeClass(data.mode); }

  // Dry run badge
  const db = document.getElementById("dry-badge");
  if (db) { db.textContent = data.dry_run ? "DRY RUN" : "LIVE"; db.className = "badge " + (data.dry_run ? "badge-yellow" : "badge-green"); }

  // Toggle
  const tg = document.getElementById("toggle");
  const tl = document.getElementById("toggle-label");
  if (tg) { tg.className = "toggle-track " + (data.auto_trading ? "on" : "off"); }
  if (tl) { tl.textContent = data.auto_trading ? "ON" : "OFF"; tl.style.color = data.auto_trading ? "#22c55e" : "#ef4444"; }

  // Indicators
  setText("ind-bbu", data.bb_upper ? "$" + data.bb_upper.toFixed(2) : "-");
  setText("ind-bbl", data.bb_lower ? "$" + data.bb_lower.toFixed(2) : "-");
  setText("ind-price", "$" + (data.price || 0).toFixed(2));
  setText("ind-macd", data.macd_up ? "UP" : (data.macd_down ? "DOWN" : "FLAT"));
  setColor("ind-macd", data.macd_up ? "#22c55e" : (data.macd_down ? "#ef4444" : "#94a3b8"));
  setText("ind-vol", data.volume_ratio ? data.volume_ratio.toFixed(2) + "x" : "-");
  setColor("ind-vol", (data.volume_ratio || 0) > 1.0 ? "#22c55e" : "#f59e0b");
  setText("ind-mom", data.momentum ? (data.momentum * 100).toFixed(1) + "%" : "-");
  setColor("ind-mom", (data.momentum || 0) > 0 ? "#22c55e" : "#ef4444");

  // Smart Money bar
  const smScore = data.sm_score || 0;
  setText("sm-score-big", (smScore >= 0 ? "+" : "") + smScore.toFixed(0));
  setColor("sm-score-big", smColor(smScore));
  const smBar = document.getElementById("sm-bar");
  const smMarker = document.getElementById("sm-marker");
  if (smBar) {
    const pct = Math.abs(smScore) / 2;
    smBar.style.width = pct + "%";
    smBar.style.left = smScore >= 0 ? "50%" : (50 - pct) + "%";
    smBar.style.background = smColor(smScore);
  }
  if (smMarker) { smMarker.style.left = (50 + smScore / 2) + "%"; }

  // Smart Money components
  const smComp = document.getElementById("sm-components");
  if (smComp && data.sm_components) {
    smComp.innerHTML = "";
    for (const [k, v] of Object.entries(data.sm_components)) {
      const div = document.createElement("div");
      div.className = "bg-gray-800 rounded p-2";
      const label = document.createElement("span");
      label.className = "text-gray-500";
      label.textContent = k + ": ";
      const val = document.createElement("span");
      val.className = "text-gray-300";
      val.textContent = v;
      div.appendChild(label);
      div.appendChild(val);
      smComp.appendChild(div);
    }
  }

  // Position
  const posCard = document.getElementById("position-card");
  if (data.has_position) {
    posCard.classList.remove("hidden");
    setText("pos-avg", "$" + (data.pos_avg || 0).toFixed(2));
    setText("pos-qty", (data.pos_qty || 0).toFixed(6));
    setText("pos-pnl", (data.pos_pnl_pct || 0).toFixed(1) + "% ($" + (data.pos_pnl_usdt || 0).toFixed(2) + ")");
    setColor("pos-pnl", pnlColor(data.pos_pnl_usdt || 0));
    setText("pos-hold", (data.pos_hold_bars || 0) + "h");
  } else {
    posCard.classList.add("hidden");
  }

  // Price chart
  if (data.price_history && data.price_history.length > 0) {
    priceChart.data.labels = data.price_history.map(p => formatTime(p.time));
    priceChart.data.datasets[0].data = data.price_history.map(p => p.price);
    priceChart.update("none");
  }

  // Footer
  setText("footer-cycle", data.cycle || 0);
  setText("footer-time", formatTime(data.last_update));

  // Settings (populate inputs from state)
  if (data.settings) { populateSettings(data.settings); }
}

// ===== Settings =====
let settingsLoaded = false;

function populateSettings(settings) {
  if (settingsLoaded) return;  // Only populate on first load
  document.querySelectorAll("[data-key]").forEach(input => {
    const key = input.dataset.key;
    if (key in settings) {
      if (input.type === "checkbox") { input.checked = settings[key]; }
      else { input.value = settings[key]; }
    }
  });
  settingsLoaded = true;
}

function saveSettings() {
  const data = {};
  document.querySelectorAll("[data-key]").forEach(input => {
    const key = input.dataset.key;
    if (input.type === "checkbox") { data[key] = input.checked; }
    else if (input.type === "number") { data[key] = parseFloat(input.value); }
    else { data[key] = input.value; }
  });
  fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  }).then(r => r.json()).then(res => {
    if (res.ok) { showToast("Settings saved"); }
    else { showToast("Error: " + (res.error || "Unknown"), true); }
  });
}

function resetDefaults() {
  fetch("/api/settings/reset", { method: "POST" })
    .then(r => r.json()).then(res => {
      if (res.ok) {
        settingsLoaded = false;
        populateSettings(res.settings);
        settingsLoaded = true;
        showToast("Reset to optimized defaults");
      }
    });
}

function toggleTrading() {
  fetch("/api/toggle", { method: "POST" })
    .then(r => r.json()).then(res => {
      const tg = document.getElementById("toggle");
      const tl = document.getElementById("toggle-label");
      if (tg) { tg.className = "toggle-track " + (res.auto_trading ? "on" : "off"); }
      if (tl) { tl.textContent = res.auto_trading ? "ON" : "OFF"; tl.style.color = res.auto_trading ? "#22c55e" : "#ef4444"; }
    });
}

// ===== Toast Notification =====
function showToast(msg, isError) {
  const toast = document.createElement("div");
  toast.style.cssText = "position:fixed;top:16px;right:16px;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;z-index:999;transition:opacity 0.5s;";
  toast.style.background = isError ? "#7f1d1d" : "#065f46";
  toast.style.color = isError ? "#fca5a5" : "#6ee7b7";
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 500); }, 3000);
}

// ===== Trade History =====
function loadTrades() {
  fetch("/api/trades?limit=50").then(r => r.json()).then(trades => {
    const tbody = document.getElementById("trade-table");
    tbody.innerHTML = "";
    trades.forEach(t => addTradeRow(t));
    setText("trade-count", trades.length + " trades");
  });
}

function loadStats() {
  fetch("/api/statistics").then(r => r.json()).then(stats => {
    setText("card-wr", stats.win_rate + "%");
    setColor("card-wr", stats.win_rate >= 50 ? "#22c55e" : "#f59e0b");
    setText("card-pnl", "$" + stats.net_pnl.toFixed(2));
    setColor("card-pnl", pnlColor(stats.net_pnl));
  });
}

function addTradeRow(t) {
  const tbody = document.getElementById("trade-table");
  const tr = document.createElement("tr");
  const sideColor = t.side === "BUY" ? "#22c55e" : "#ef4444";
  tr.innerHTML = `
    <td style="color:#94a3b8">${formatDate(t.timestamp)}</td>
    <td style="color:${sideColor};font-weight:600">${t.side}</td>
    <td>$${(t.price||0).toFixed(2)}</td>
    <td>${(t.quantity||0).toFixed(6)}</td>
    <td><span class="badge ${modeBadgeClass(t.mode)}">${t.mode||'-'}</span></td>
    <td style="color:${pnlColor(t.pnl_percent)}">${t.pnl_percent ? t.pnl_percent.toFixed(1)+'%' : '-'}</td>
    <td style="color:${pnlColor(t.pnl_usdt)}">$${(t.pnl_usdt||0).toFixed(2)}</td>
    <td>${t.holding_bars||0}h</td>
    <td>${(t.smart_money_score||0).toFixed(0)}</td>
  `;
  tbody.prepend(tr);
}

// ===== SocketIO Events (optional, graceful fallback) =====
if (socket) {
  socket.on("connect", () => {
    console.log("Connected to bot via WebSocket");
    loadTrades();
    loadStats();
  });
  socket.on("cycle_update", data => { updateDashboard(data); });
  socket.on("trade_executed", trade => {
    addTradeRow(trade);
    loadStats();
    showToast(`Trade: ${trade.side} @ $${trade.price.toFixed(2)}`);
  });
}

// ===== HTTP Polling (primary data source) =====
function pollState() {
  fetch("/api/state")
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(data => { updateDashboard(data); })
    .catch(() => {});
}
pollState();
loadTrades();
loadStats();
setInterval(pollState, 3000);
setInterval(loadTrades, 15000);
setInterval(loadStats, 15000);
