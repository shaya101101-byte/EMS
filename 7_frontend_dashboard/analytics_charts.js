// analytics_charts.js - fetch /analytics-data and render charts using Chart.js
(function(){
  async function fetchData(){
    try{
      const res = await fetch('http://127.0.0.1:8000/analytics-data');
      if(!res.ok) throw new Error('Failed to load analytics data');
      return await res.json();
    }catch(e){ console.error(e); return null }
  }

  function createBar(ctx, labels, values){
    return new Chart(ctx, {
      type: 'bar',
      data: { labels: labels, datasets: [{ label: 'Count', data: values, backgroundColor: '#1F6FEB' }] },
      options: { responsive:true, plugins:{ legend:{ display:false } }, scales:{ y:{ beginAtZero:true } } }
    });
  }

  function createPie(ctx, labels, values){
    return new Chart(ctx, {
      type: 'pie',
      data: { labels: labels, datasets: [{ data: values, backgroundColor: ['#27AE60','#FFA500','#FF6B6B'] }] },
      options: { responsive:true }
    });
  }

  function createLine(ctx, labels, values){
    return new Chart(ctx, {
      type: 'line',
      data: { labels: labels, datasets: [{ label: 'Detections', data: values, borderColor: '#1F6FEB', backgroundColor: 'rgba(31,111,235,0.08)', fill:true }] },
      options: { responsive:true, scales:{ y:{ beginAtZero:true } } }
    });
  }

  async function render(){
    const data = await fetchData();
    if(!data) return;

    // speciesCounts -> bar
    const species = data.speciesCounts || {};
    const speciesLabels = Object.keys(species);
    const speciesValues = speciesLabels.map(k=>species[k]);

    // safetyStats -> pie
    const safety = data.safetyStats || {safe:0,warning:0,dangerous:0};
    const safetyLabels = ['Safe','Warning','Dangerous'];
    const safetyValues = [safety.safe||0, safety.warning||0, safety.dangerous||0];

    // dailyTrend -> line
    const trend = data.dailyTrend || [];
    const trendLabels = trend.map(d=>d.date);
    const trendValues = trend.map(d=>d.count);

    // render charts if canvases exist
    const barEl = document.getElementById('speciesBarChart');
    const pieEl = document.getElementById('safetyPieChart');
    const lineEl = document.getElementById('trendLineChart');

    if(barEl && speciesLabels.length){ createBar(barEl.getContext('2d'), speciesLabels, speciesValues); }
    if(pieEl){ createPie(pieEl.getContext('2d'), safetyLabels, safetyValues); }
    if(lineEl){ createLine(lineEl.getContext('2d'), trendLabels, trendValues); }
  }

  // wait for DOM
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', render);
  } else render();
})();
