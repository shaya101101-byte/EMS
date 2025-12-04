// live_dashboard.js - fetch stats and update UI
let autoRefresh = false;
let autoRefreshInterval = null;

const ctx = document.getElementById('turbidityChart') && document.getElementById('turbidityChart').getContext('2d');
let turbidityChart = null;

function makeChart(labels = [], data = []){
  if(!ctx) return;
  if(turbidityChart){
    turbidityChart.data.labels = labels;
    turbidityChart.data.datasets[0].data = data;
    turbidityChart.update();
    return;
  }

  turbidityChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Turbidity (NTU)',
        data: data,
        borderColor: '#1976d2',
        backgroundColor: 'rgba(25,118,210,0.08)',
        tension: 0.25,
        pointRadius: 2
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { display: true }, y: { beginAtZero: true } }
    }
  });
}

async function refreshStats(){
  const url = 'http://127.0.0.1:8000/api/stats?hours=24';
  try{
    const res = await fetch(url);
    if(!res.ok) throw new Error('Server error: '+res.status);
    const json = await res.json();

    // Update current values
    const c = json.current || {};
    document.getElementById('turbidityValue').textContent = (c.turbidity ?? '--');
    document.getElementById('phValue').textContent = (c.ph ?? '--');
    document.getElementById('tempValue').textContent = (c.temperature ?? '--');
    document.getElementById('doValue').textContent = (c.do_level ?? '--');
    document.getElementById('tdsValue').textContent = (c.tds ?? '--');
    document.getElementById('condValue').textContent = (c.conductivity ?? '--');

    // Update chart with history
    const history = json.history || [];
    const labels = history.map(h => h.hour);
    const data = history.map(h => h.turbidity);
    makeChart(labels, data);
  }catch(err){
    console.error('refreshStats error', err);
    // keep existing UI; show simple inline message - don't block page load
    console.warn('Could not fetch live data: '+err.message);
  }
}

// Auto-refresh toggle
function toggleAutoRefresh(){
  autoRefresh = !autoRefresh;
  const btn = document.getElementById('autoRefreshBtn');
  if(autoRefresh){
    btn.textContent = 'Stop Auto-Refresh';
    btn.classList.remove('secondary');
    autoRefreshInterval = setInterval(refreshStats, 60*1000);
  } else {
    btn.textContent = 'Start Auto-Refresh';
    btn.classList.add('secondary');
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }
}

// Wire up buttons
window.addEventListener('DOMContentLoaded', () =>{
  document.getElementById('refreshBtn').addEventListener('click', refreshStats);
  document.getElementById('autoRefreshBtn').addEventListener('click', toggleAutoRefresh);

  // initialize chart with empty data
  makeChart([], []);

  // initial fetch (safe to fail)
  refreshStats();
});
