const $ = (id) => document.getElementById(id);

const metricMeta = {
  temperature_c: {label: 'Temperature', unit: '°C'},
  humidity_pct: {label: 'Humidity', unit: '%'},
  pm25_ug_m3: {label: 'PM2.5', unit: ' µg/m³'},
  pm10_ug_m3: {label: 'PM10', unit: ' µg/m³'},
  co2_ppm: {label: 'CO₂', unit: ' ppm'},
  noise_db: {label: 'Noise', unit: ' dB'},
  estimated_aqi: {label: 'Estimated AQI', unit: ''},
  environmental_health_score: {label: 'Health score', unit: '/100'}
};

let stations = [];
let stationById = new Map();
let liveReadings = [];
let recentAlerts = [];
let map;
let mapMarkers = new Map();
let mapMode = 'live';
let playbackFrames = [];
let playbackTimer = null;
let historySeries = null;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

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
  return `<article class="station-card" data-station="${r.station_id}">
    <div class="station-head">
      <div><h3>${r.station_name}</h3><small>${r.source.toUpperCase()}</small></div>
      <span class="health-pill">${r.environmental_health_score}/100</span>
    </div>
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

function mergeAlerts(incoming) {
  if (!incoming?.length) return;
  const existing = new Set(recentAlerts.map(a => a.id));
  for (const alert of incoming) {
    if (!existing.has(alert.id)) recentAlerts.unshift(alert);
  }
  recentAlerts = recentAlerts.slice(0, 20);
}

function renderAlerts() {
  if (!recentAlerts.length) {
    $('alerts').innerHTML = '<p class="muted">No alerts yet.</p>';
    return;
  }
  $('alerts').innerHTML = recentAlerts.slice(0, 8).map(a =>
    `<div class="alert ${a.severity}">
      <strong>${a.severity.toUpperCase()} · ${a.title}</strong>
      <span>${a.message}</span>
    </div>`
  ).join('');
}

function render(payload) {
  const readings = payload.readings || [];
  const summary = payload.summary || {};
  liveReadings = readings.length ? readings : liveReadings;

  if (readings.length) $('stations').innerHTML = readings.map(stationCard).join('');
  $('network-score').textContent = summary.average_health_score ?? '--';
  $('network-status').textContent = statusFromScore(summary.average_health_score ?? 0);
  $('station-count').textContent = summary.stations ?? readings.length;
  $('scenario').textContent = (payload.scenario || 'baseline').replaceAll('_',' ');
  $('last-update').textContent = `Updated ${new Date().toLocaleTimeString()}`;

  if (summary.worst_station && summary.best_station) {
    $('insight').textContent =
      `${summary.best_station.name} currently has the strongest environmental health score ` +
      `(${summary.best_station.score}/100), while ${summary.worst_station.name} is under the ` +
      `most pressure (${summary.worst_station.score}/100). All current values are simulated.`;
  }

  mergeAlerts(payload.alerts || []);
  renderAlerts();

  if (mapMode === 'live' && map) {
    renderMap(liveReadings, 'LIVE');
  }
}

function pressure(metricName, value) {
  const v = Number(value || 0);
  switch (metricName) {
    case 'pm25_ug_m3': return clamp(v / 100, 0, 1);
    case 'pm10_ug_m3': return clamp(v / 220, 0, 1);
    case 'co2_ppm': return clamp((v - 400) / 1200, 0, 1);
    case 'noise_db': return clamp((v - 35) / 60, 0, 1);
    case 'temperature_c': return clamp(Math.abs(v - 24) / 22, 0, 1);
    case 'environmental_health_score': return clamp(1 - v / 100, 0, 1);
    default: return .4;
  }
}

function markerColor(metricName, value) {
  const p = pressure(metricName, value);
  const hue = Math.round(120 * (1 - p));
  return `hsl(${hue} 78% 52%)`;
}

function initMap() {
  if (!window.L || !stations.length) return;
  const lat = stations.reduce((sum, s) => sum + s.latitude, 0) / stations.length;
  const lon = stations.reduce((sum, s) => sum + s.longitude, 0) / stations.length;

  map = L.map('map', {zoomControl: true, attributionControl: true}).setView([lat, lon], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  setTimeout(() => map.invalidateSize(), 120);
}

function renderMap(readings, modeLabel) {
  if (!map || !readings?.length) return;
  const metricName = $('map-metric').value;
  const meta = metricMeta[metricName];

  for (const reading of readings) {
    const station = stationById.get(reading.station_id);
    if (!station) continue;

    const value = reading[metricName];
    const p = pressure(metricName, value);
    const color = markerColor(metricName, value);
    const radius = 12 + p * 22;

    let marker = mapMarkers.get(reading.station_id);
    if (!marker) {
      marker = L.circleMarker([station.latitude, station.longitude], {
        radius,
        color,
        weight: 2,
        fillColor: color,
        fillOpacity: .48
      }).addTo(map);
      mapMarkers.set(reading.station_id, marker);
    } else {
      marker.setStyle({color, fillColor: color, fillOpacity: .48});
      marker.setRadius(radius);
    }

    const time = reading.timestamp ? new Date(reading.timestamp).toLocaleString() : '—';
    marker.bindPopup(`
      <div class="map-popup">
        <strong>${station.name}</strong>
        <span>${meta.label}: <b>${value}${meta.unit}</b></span>
        <span>Health: <b>${reading.environmental_health_score}/100</b></span>
        <span>Scenario: <b>${String(reading.scenario).replaceAll('_',' ')}</b></span>
        <small>${time} · ${String(reading.source).toUpperCase()}</small>
      </div>
    `);
  }

  $('map-mode').textContent = modeLabel;
}

async function loadInitial() {
  const [stationData, readings, summary, alerts, overview] = await Promise.all([
    fetch('/api/stations').then(r => r.json()),
    fetch('/api/latest').then(r => r.json()),
    fetch('/api/summary').then(r => r.json()),
    fetch('/api/alerts?limit=8').then(r => r.json()),
    fetch('/api/history/overview?minutes=1440').then(r => r.json())
  ]);

  stations = stationData;
  stationById = new Map(stations.map(s => [s.id, s]));
  recentAlerts = alerts;

  const selector = $('history-station');
  selector.innerHTML = stations.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
  selector.value = stations.some(s => s.id === 'industrial') ? 'industrial' : stations[0]?.id;

  initMap();
  render({readings, summary, alerts, scenario: summary.scenario});
  renderOverview(overview);
  $('history-samples').textContent = `${overview.samples || 0} samples`;

  await Promise.all([loadHistorySeries(), loadPlayback()]);
}

function renderOverview(overview) {
  const rows = overview.station_summary || [];
  $('daily-overview').innerHTML = rows.slice(0, 5).map(row => `
    <div class="overview-row">
      <span>${row.station_name}</span>
      <strong>${row.avg_health}/100</strong>
      <small>PM2.5 avg ${row.avg_pm25} · peak ${row.max_pm25}</small>
    </div>
  `).join('') || '<p class="muted">No history yet.</p>';
}

async function refreshOverview() {
  const overview = await fetch('/api/history/overview?minutes=1440').then(r => r.json());
  renderOverview(overview);
  $('history-samples').textContent = `${overview.samples || 0} samples`;
}

async function loadHistorySeries() {
  const stationId = $('history-station').value;
  const metricName = $('history-metric').value;
  const minutes = $('history-window').value;
  if (!stationId) return;

  const response = await fetch(
    `/api/history?station_id=${encodeURIComponent(stationId)}&metric=${encodeURIComponent(metricName)}&minutes=${minutes}&limit=1800`
  );
  historySeries = await response.json();
  drawHistoryChart();
}

function drawHistoryChart() {
  if (!historySeries) return;
  const canvas = $('history-chart');
  const box = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(box.width));
  const height = 270;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, width, height);
  const points = historySeries.points || [];
  const meta = historySeries.meta || {label: historySeries.metric, unit: ''};

  if (points.length < 2) {
    ctx.fillStyle = '#94b5a8';
    ctx.font = '14px system-ui';
    ctx.fillText('Not enough historical data yet.', 20, 40);
    $('chart-caption').textContent = 'History will grow automatically while EcoPulse AI runs.';
    return;
  }

  const values = points.map(p => Number(p.value));
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) { min -= 1; max += 1; }
  const pad = (max - min) * .12;
  min -= pad; max += pad;

  const left = 54, right = 18, top = 20, bottom = 36;
  const plotW = width - left - right;
  const plotH = height - top - bottom;

  ctx.strokeStyle = 'rgba(148,181,168,.16)';
  ctx.lineWidth = 1;
  ctx.fillStyle = '#94b5a8';
  ctx.font = '11px system-ui';

  for (let i = 0; i <= 4; i++) {
    const y = top + (plotH / 4) * i;
    const value = max - ((max - min) / 4) * i;
    ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(width - right, y); ctx.stroke();
    ctx.fillText(value.toFixed(1), 6, y + 4);
  }

  const start = new Date(points[0].timestamp);
  const end = new Date(points[points.length - 1].timestamp);
  ctx.fillText(start.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}), left, height - 10);
  const endLabel = end.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  const endWidth = ctx.measureText(endLabel).width;
  ctx.fillText(endLabel, width - right - endWidth, height - 10);

  const gradient = ctx.createLinearGradient(0, top, 0, top + plotH);
  gradient.addColorStop(0, 'rgba(86,243,165,.22)');
  gradient.addColorStop(1, 'rgba(86,243,165,0)');

  const coords = points.map((p, i) => {
    const x = left + (i / (points.length - 1)) * plotW;
    const y = top + (1 - (Number(p.value) - min) / (max - min)) * plotH;
    return [x, y];
  });

  ctx.beginPath();
  coords.forEach(([x,y], i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y));
  ctx.lineTo(coords[coords.length-1][0], top + plotH);
  ctx.lineTo(coords[0][0], top + plotH);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  coords.forEach(([x,y], i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y));
  ctx.strokeStyle = '#56f3a5';
  ctx.lineWidth = 2.3;
  ctx.stroke();

  const station = stationById.get(historySeries.station_id);
  $('chart-caption').textContent =
    `${station?.name || historySeries.station_id} · ${meta.label} · ${points.length} points · ` +
    `range ${Math.min(...values).toFixed(1)}–${Math.max(...values).toFixed(1)}${meta.unit}`;
}

async function loadPlayback() {
  stopPlayback();
  const minutes = $('playback-window').value;
  const data = await fetch(`/api/playback?minutes=${minutes}&max_frames=180`).then(r => r.json());
  playbackFrames = data.frames || [];
  const slider = $('playback-slider');
  slider.max = Math.max(0, playbackFrames.length - 1);
  slider.value = Math.max(0, playbackFrames.length - 1);
  $('timeline-note').textContent = playbackFrames.length
    ? `${playbackFrames.length} sampled frames available.`
    : 'No historical frames available yet.';
  if (playbackFrames.length) showPlaybackFrame(Number(slider.value), false);
}

function showPlaybackFrame(index, switchMode = true) {
  const frame = playbackFrames[index];
  if (!frame) return;
  if (switchMode) mapMode = 'playback';
  $('playback-clock').textContent = new Date(frame.timestamp).toLocaleString();
  renderMap(frame.readings, 'TIME MACHINE');
}

function stopPlayback() {
  if (playbackTimer) clearInterval(playbackTimer);
  playbackTimer = null;
  $('playback-toggle').textContent = '▶ Play';
}

function togglePlayback() {
  if (!playbackFrames.length) return;
  if (playbackTimer) {
    stopPlayback();
    return;
  }

  mapMode = 'playback';
  $('playback-toggle').textContent = '❚❚ Pause';
  playbackTimer = setInterval(() => {
    const slider = $('playback-slider');
    let next = Number(slider.value) + 1;
    if (next >= playbackFrames.length) next = 0;
    slider.value = next;
    showPlaybackFrame(next);
  }, 650);
}

function returnLive() {
  stopPlayback();
  mapMode = 'live';
  renderMap(liveReadings, 'LIVE');
  $('playback-clock').textContent = 'Live environmental network';
}

function connect() {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${location.host}/ws/environment`);
  let heartbeat;

  socket.onmessage = (event) => render(JSON.parse(event.data));
  socket.onopen = () => {
    heartbeat = setInterval(() => socket.readyState === 1 && socket.send('ping'), 15000);
  };
  socket.onclose = () => {
    clearInterval(heartbeat);
    setTimeout(connect, 1500);
  };
}

document.querySelectorAll('[data-scenario]').forEach(button => {
  button.addEventListener('click', async () => {
    document.querySelectorAll('[data-scenario]').forEach(b => b.classList.remove('active'));
    button.classList.add('active');
    const scenario = button.dataset.scenario;
    const response = await fetch(`/api/scenarios/${scenario}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({intensity: 1.0})
    });
    const data = await response.json();
    const summary = await fetch('/api/summary').then(r => r.json());
    render({readings: data.readings, summary, scenario, alerts: []});
    setTimeout(refreshOverview, 300);
  });
});

$('map-metric').addEventListener('change', () => {
  if (mapMode === 'live') renderMap(liveReadings, 'LIVE');
  else showPlaybackFrame(Number($('playback-slider').value));
});

$('playback-window').addEventListener('change', loadPlayback);
$('playback-slider').addEventListener('input', event => {
  stopPlayback();
  showPlaybackFrame(Number(event.target.value));
});
$('playback-toggle').addEventListener('click', togglePlayback);
$('return-live').addEventListener('click', returnLive);

['history-station','history-metric','history-window'].forEach(id => {
  $(id).addEventListener('change', loadHistorySeries);
});

window.addEventListener('resize', () => {
  if (historySeries) drawHistoryChart();
  if (map) setTimeout(() => map.invalidateSize(), 80);
});

loadInitial().catch(error => {
  console.error(error);
  $('network-status').textContent = 'Could not load the EcoPulse API.';
});
connect();
