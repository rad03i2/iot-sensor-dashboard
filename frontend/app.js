const $ = (id) => document.getElementById(id);

function statusFromScore(score) {
  if (score >= 85) return 'Excellent environmental conditions';
  if (score >= 70) return 'Good overall conditions';
  if (score >= 50) return 'Moderate environmental pressure';
  return 'High environmental pressure detected';
}

function metric(label, value, unit='') {
  return `<div class="metric"><span>${label}</span><strong>${value}${unit}</strong></div>`;
}

function stationCard(r) {
  return `<article class="station-card">
    <div class="station-head"><div><h3>${r.station_name}</h3><small>${r.source.toUpperCase()}</small></div><span class="health-pill">${r.environmental_health_score}/100</span></div>
    <div class="metrics">
      ${metric('PM2.5', r.pm25_ug_m3, ' µg/m³')}
      ${metric('PM10', r.pm10_ug_m3, ' µg/m³')}
      ${metric('CO₂', r.co2_ppm, ' ppm')}
      ${metric('Noise', r.noise_db, ' dB')}
      ${metric('Temperature', r.temperature_c, '°C')}
      ${metric('Humidity', r.humidity_pct, '%')}
      ${metric('Est. AQI', r.estimated_aqi)}
      ${metric('Scenario', r.scenario.replaceAll('_',' '))}
    </div>
  </article>`;
}

function render(payload) {
  const readings = payload.readings || [];
  const summary = payload.summary || {};
  $('stations').innerHTML = readings.map(stationCard).join('');
  $('network-score').textContent = summary.average_health_score ?? '--';
  $('network-status').textContent = statusFromScore(summary.average_health_score ?? 0);
  $('station-count').textContent = summary.stations ?? readings.length;
  $('scenario').textContent = (payload.scenario || 'baseline').replaceAll('_',' ');
  $('last-update').textContent = `Updated ${new Date().toLocaleTimeString()}`;
  if (summary.worst_station && summary.best_station) {
    $('insight').textContent = `${summary.best_station.name} currently has the strongest environmental health score (${summary.best_station.score}/100), while ${summary.worst_station.name} is under the most pressure (${summary.worst_station.score}/100). All current values are simulated.`;
  }
  const alerts = payload.alerts || [];
  if (alerts.length) {
    $('alerts').innerHTML = alerts.slice(0,8).map(a => `<div class="alert ${a.severity}"><strong>${a.severity.toUpperCase()} · ${a.title}</strong><span>${a.message}</span></div>`).join('');
  }
}

async function loadInitial() {
  const [readings, summary, alerts] = await Promise.all([
    fetch('/api/latest').then(r => r.json()),
    fetch('/api/summary').then(r => r.json()),
    fetch('/api/alerts?limit=8').then(r => r.json())
  ]);
  render({readings, summary, alerts, scenario: summary.scenario});
}

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${location.host}/ws/environment`);
  socket.onmessage = (event) => render(JSON.parse(event.data));
  socket.onclose = () => setTimeout(connect, 1500);
  socket.onopen = () => setInterval(() => socket.readyState === 1 && socket.send('ping'), 15000);
}

document.querySelectorAll('[data-scenario]').forEach(button => {
  button.addEventListener('click', async () => {
    document.querySelectorAll('[data-scenario]').forEach(b => b.classList.remove('active'));
    button.classList.add('active');
    const scenario = button.dataset.scenario;
    const response = await fetch(`/api/scenarios/${scenario}`, {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({intensity: 1.0})
    });
    const data = await response.json();
    render({readings:data.readings, summary:{...await fetch('/api/summary').then(r=>r.json())}, scenario, alerts:[]});
  });
});

loadInitial().catch(console.error);
connect();
