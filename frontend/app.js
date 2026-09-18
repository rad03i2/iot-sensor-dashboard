const $ = id => document.getElementById(id);
const MOSUL = [36.335, 43.118889];
let map = null;
let cityMarker = null;
let focusCircle = null;
let lastSnapshot = null;
let retryDelay = 5000;
let sceneIndex = 0;

const scenes = [
  {key:'air', label:'جودة الهواء', source:'CAMS Global', type:'نموذج جوي'},
  {key:'dust', label:'الغبار', source:'CAMS Global', type:'نموذج غبار جوي'},
  {key:'weather', label:'الطقس والرياح', source:'Open-Meteo', type:'نموذج طقس'},
  {key:'river', label:'نهر دجلة', source:'GloFAS v4', type:'نموذج هيدرولوجي'}
];

const weatherText = {
  0:'صحو',1:'صحو غالباً',2:'غائم جزئياً',3:'غائم',45:'ضباب',48:'ضباب متجمد',
  51:'رذاذ خفيف',53:'رذاذ',55:'رذاذ كثيف',61:'مطر خفيف',63:'مطر',65:'مطر غزير',
  71:'ثلج خفيف',73:'ثلج',75:'ثلج غزير',80:'زخات خفيفة',81:'زخات',82:'زخات غزيرة',
  95:'عاصفة رعدية',96:'عاصفة رعدية مع برد',99:'عاصفة رعدية شديدة'
};

const num = (v, digits=0) => {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(digits) : '--';
};

function sectionData(snapshot, key) {
  return (snapshot && snapshot[key] && snapshot[key].data) || {};
}

function aqiLabel(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return 'غير متاح';
  if (v <= 50) return 'جيد';
  if (v <= 100) return 'متوسط';
  if (v <= 150) return 'غير صحي للفئات الحساسة';
  if (v <= 200) return 'غير صحي';
  if (v <= 300) return 'غير صحي جداً';
  return 'خطر';
}

function aqiColor(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return '#78958c';
  if (v <= 50) return '#4ce0a3';
  if (v <= 100) return '#ead36e';
  if (v <= 150) return '#f5a45e';
  if (v <= 200) return '#ff6f7c';
  return '#bc7cff';
}

function initMap() {
  map = L.map('map', {
    zoomControl:false,
    attributionControl:true,
    dragging:false,
    scrollWheelZoom:false,
    doubleClickZoom:false,
    boxZoom:false,
    keyboard:false,
    tap:false
  }).setView(MOSUL, 11.25);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom:19,
    attribution:'© OpenStreetMap'
  }).addTo(map);

  cityMarker = L.circleMarker(MOSUL, {
    radius:6,
    color:'#dffff4',
    weight:2,
    fillColor:'#4ce0a3',
    fillOpacity:1
  }).addTo(map).bindTooltip('الموصل', {
    permanent:true,
    direction:'top',
    className:'mosul-label'
  });

  focusCircle = L.circle(MOSUL, {
    radius:12000,
    color:'#4ce0a3',
    weight:2,
    opacity:.78,
    fillColor:'#4ce0a3',
    fillOpacity:.13
  }).addTo(map);

  setTimeout(() => map.invalidateSize(), 120);
}

function tickClock() {
  const now = new Date();
  $('clock').textContent = new Intl.DateTimeFormat('ar-IQ', {
    timeZone:'Asia/Baghdad',
    hour:'2-digit',
    minute:'2-digit',
    second:'2-digit',
    hour12:false
  }).format(now);
  $('date').textContent = new Intl.DateTimeFormat('ar-IQ', {
    timeZone:'Asia/Baghdad',
    weekday:'long',
    year:'numeric',
    month:'long',
    day:'numeric'
  }).format(now);
}

function render(snapshot) {
  lastSnapshot = snapshot;
  const weather = sectionData(snapshot,'weather');
  const air = sectionData(snapshot,'air');
  const river = sectionData(snapshot,'river');
  const wc = weather.current || {};
  const ac = air.current || {};
  const rc = river.current || {};
  const aqi = Number(ac.us_aqi);

  $('k-temp').textContent = num(wc.temperature_c,1) + '°';
  $('k-humidity').textContent = num(wc.humidity_pct) + '%';
  $('k-pm25').textContent = num(ac.pm25_ug_m3,1);
  $('k-pm10').textContent = num(ac.pm10_ug_m3,1);
  $('k-aqi').textContent = num(ac.us_aqi);
  $('k-aqi-label').textContent = aqiLabel(ac.us_aqi) + ' · CAMS';
  $('k-aqi').style.color = aqiColor(ac.us_aqi);
  $('k-dust').textContent = num(ac.dust_ug_m3,1);
  $('k-uv').textContent = num(ac.uv_index,1);

  $('hero-aqi').textContent = num(ac.us_aqi);
  $('hero-aqi-label').textContent = aqiLabel(ac.us_aqi);
  $('aqi-ring').style.setProperty('--ring-color', aqiColor(ac.us_aqi));
  const progress = Number.isFinite(aqi) ? Math.min(Math.max(aqi / 200, 0), 1) * 100 : 0;
  $('aqi-ring').style.setProperty('--aqi-progress', progress + '%');

  $('weather-condition').textContent = weatherText[wc.weather_code] || 'الطقس';
  $('feels').textContent = num(wc.apparent_temperature_c,1) + '°C';
  $('wind').textContent = num(wc.wind_speed_kmh,1) + ' كم/س';
  $('pressure').textContent = num(wc.pressure_msl_hpa) + ' hPa';
  $('visibility').textContent = num(wc.visibility_km,1) + ' كم';

  $('no2').textContent = num(ac.nitrogen_dioxide_ug_m3,1);
  $('so2').textContent = num(ac.sulphur_dioxide_ug_m3,1);
  $('o3').textContent = num(ac.ozone_ug_m3,1);
  $('aod').textContent = num(ac.aerosol_optical_depth,2);

  $('river-discharge').textContent = rc.river_discharge_m3_s == null
    ? 'غير متاح'
    : num(rc.river_discharge_m3_s,1) + ' م³/ث';

  const change = Number(rc.daily_change_pct);
  $('river-trend').textContent = Number.isFinite(change)
    ? (change >= 0 ? '▲ ' : '▼ ') + Math.abs(change).toFixed(1) + '% يومياً'
    : 'لا توجد مقارنة يومية';
  $('river-trend').className = Number.isFinite(change)
    ? (change >= 0 ? 'up' : 'down') : '';

  $('brief').textContent = snapshot.brief_ar || 'بانتظار البيانات.';
  renderSources(snapshot);
  renderForecast(weather.daily_5d || []);
  renderAlerts(snapshot.alerts || []);
  drawAirChart(air.hourly_24h || []);
  renderFreshness(snapshot);
  renderScene();
}

function renderScene() {
  if (!lastSnapshot) return;
  const scene = scenes[sceneIndex];
  const weather = sectionData(lastSnapshot,'weather');
  const air = sectionData(lastSnapshot,'air');
  const river = sectionData(lastSnapshot,'river');
  const wc = weather.current || {};
  const ac = air.current || {};
  const rc = river.current || {};

  let value = '--';
  let copy = '';
  let color = '#4ce0a3';
  let radius = 12000;

  if (scene.key === 'air') {
    value = 'AQI ' + num(ac.us_aqi);
    copy = 'حالة جودة الهواء النموذجية فوق الموصل وفق Copernicus CAMS، وليست قراءة حساس أرضي.';
    color = aqiColor(ac.us_aqi);
    radius = 12500;
  } else if (scene.key === 'dust') {
    value = num(ac.dust_ug_m3,1) + ' µg/m³';
    copy = 'تركيز الغبار النموذجي في طبقة CAMS العالمية فوق منطقة الموصل.';
    color = '#d6a467';
    radius = 14500;
  } else if (scene.key === 'weather') {
    value = num(wc.temperature_c,1) + '°C · ' + num(wc.wind_speed_kmh,1) + ' كم/س';
    copy = 'الطقس الحالي واتجاه الظروف الجوية حول الموصل وفق نموذج Open-Meteo.';
    color = '#58cdec';
    radius = 11000;
  } else {
    value = rc.river_discharge_m3_s == null ? 'غير متاح' : num(rc.river_discharge_m3_s,1) + ' م³/ث';
    copy = 'تقدير GloFAS لتصريف خلية نهرية قرب الموصل، وليس قياس محطة محلية على دجلة.';
    color = '#5a9cff';
    radius = 9000;
  }

  $('scene-focus').textContent = scene.label;
  $('scene-counter').textContent = String(sceneIndex + 1).padStart(2,'0');
  $('map-source').textContent = scene.source;
  $('map-source-type').textContent = scene.type;
  $('map-focus-label').textContent = scene.label;
  $('map-focus-value').textContent = value;
  $('map-focus-copy').textContent = copy;

  if (focusCircle) {
    focusCircle.setRadius(radius);
    focusCircle.setStyle({
      color:color,
      fillColor:color,
      fillOpacity:.13
    });
  }
}

function rotateScene() {
  sceneIndex = (sceneIndex + 1) % scenes.length;
  renderScene();
}

function renderSources(snapshot) {
  const items = [
    ['الطقس', snapshot.weather],
    ['الهواء', snapshot.air],
    ['دجلة', snapshot.river]
  ];

  $('source-status').innerHTML = items.map(item => {
    const label = item[0];
    const section = item[1] || {};
    const status = section.status || 'unavailable';
    const text = status === 'ok'
      ? 'متصل'
      : status === 'stale'
        ? 'آخر قراءة محفوظة'
        : 'غير متاح';
    return '<div><span><i class="' + status + '"></i>' + label +
      '</span><b>' + text + '</b></div>';
  }).join('');
}

function renderForecast(days) {
  $('forecast').innerHTML = days.slice(0,5).map(day => {
    const date = day.date ? new Date(day.date + 'T12:00:00') : null;
    const dayName = date
      ? new Intl.DateTimeFormat('ar-IQ',{weekday:'short'}).format(date)
      : '--';
    return '<div class="forecast-day">' +
      '<b>' + dayName + '</b>' +
      '<span>' + (weatherText[day.weather_code] || '—') + '</span>' +
      '<strong>' + num(day.temperature_max_c) + '°</strong>' +
      '<small>' + num(day.temperature_min_c) + '° · مطر ' +
      num(day.precipitation_probability_max_pct) + '%</small></div>';
  }).join('') || '<div class="empty">التوقعات غير متاحة مؤقتاً</div>';
}

function renderAlerts(alerts) {
  const visible = alerts.slice(0,3);
  $('alerts').innerHTML = visible.map(a =>
    '<div class="event ' + (a.severity || 'info') + '">' +
      '<span>' + (a.icon || '●') + '</span>' +
      '<div><b>' + a.title + '</b><small>' + a.message + '</small></div>' +
    '</div>'
  ).join('') || '<div class="event info"><span>●</span><div><b>لا توجد تنبيهات</b></div></div>';

  const important = alerts.find(a => a.severity === 'critical') ||
                    alerts.find(a => a.severity === 'warning');

  const ribbon = $('alert-ribbon');
  if (important) {
    ribbon.classList.add('active');
    ribbon.classList.toggle('critical', important.severity === 'critical');
    $('alert-ribbon-title').textContent = important.title;
    $('alert-ribbon-message').textContent = important.message;
  } else {
    ribbon.classList.remove('active','critical');
    $('alert-ribbon-title').textContent = 'المرصد يعمل بشكل طبيعي';
    $('alert-ribbon-message').textContent = 'لا توجد تنبيهات بارزة حالياً.';
  }
}

function renderFreshness(snapshot) {
  const refresh = snapshot.last_refresh ? new Date(snapshot.last_refresh) : null;
  const dot = $('live-dot');

  if (!refresh || Number.isNaN(refresh.getTime())) {
    $('freshness').textContent = 'بانتظار أول تحديث';
    $('last-refresh').textContent = 'آخر تحديث: --';
    dot.className = 'signal-dot bad';
    return;
  }

  const ageMin = Math.max(0, Math.round((Date.now() - refresh.getTime()) / 60000));
  $('freshness').textContent = ageMin <= 10
    ? 'المصادر البيئية متصلة'
    : 'آخر تحديث منذ ' + ageMin + ' دقيقة';

  $('last-refresh').textContent = 'آخر تحديث ' + new Intl.DateTimeFormat('ar-IQ',{
    timeZone:'Asia/Baghdad',
    hour:'2-digit',
    minute:'2-digit',
    hour12:false
  }).format(refresh);

  dot.className = 'signal-dot' + (ageMin > 20 ? ' warn' : '');
}

function drawAirChart(rows) {
  const canvas = $('air-chart');
  const box = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(420, Math.floor(box.width));
  const height = Math.max(120, Math.floor(box.height || 132));

  canvas.width = width * dpr;
  canvas.height = height * dpr;

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,width,height);

  const points = rows.filter(r =>
    Number.isFinite(Number(r.pm25_ug_m3)) ||
    Number.isFinite(Number(r.dust_ug_m3))
  );

  if (points.length < 2) {
    ctx.fillStyle='#78958b';
    ctx.font='12px Segoe UI';
    ctx.fillText('لا تتوفر سلسلة 24 ساعة حالياً',16,32);
    return;
  }

  const values = points.flatMap(r => [
    Number(r.pm25_ug_m3) || 0,
    Number(r.dust_ug_m3) || 0
  ]);
  const max = Math.max(10,...values) * 1.12;
  const left=34, right=10, top=10, bottom=24;
  const plotW=width-left-right, plotH=height-top-bottom;

  ctx.strokeStyle='rgba(173,219,203,.10)';
  ctx.lineWidth=1;
  for (let i=0;i<4;i++) {
    const y=top+plotH*i/3;
    ctx.beginPath();
    ctx.moveTo(left,y);
    ctx.lineTo(width-right,y);
    ctx.stroke();
  }

  function drawLine(key,color) {
    ctx.beginPath();
    points.forEach((p,i) => {
      const x=left+(i/(points.length-1))*plotW;
      const value=Number(p[key]) || 0;
      const y=top+plotH-(value/max)*plotH;
      if (i) ctx.lineTo(x,y); else ctx.moveTo(x,y);
    });
    ctx.strokeStyle=color;
    ctx.lineWidth=2.4;
    ctx.shadowColor=color;
    ctx.shadowBlur=8;
    ctx.stroke();
    ctx.shadowBlur=0;
  }

  drawLine('dust_ug_m3','#d6a467');
  drawLine('pm25_ug_m3','#4ce0a3');

  ctx.fillStyle='#6f9487';
  ctx.font='10px Segoe UI';
  const formatTime = t => t
    ? new Date(t).toLocaleTimeString('ar-IQ',{hour:'2-digit',minute:'2-digit'})
    : '--';
  ctx.fillText(formatTime(points[0].time),left,height-6);
  const endLabel=formatTime(points[points.length-1].time);
  const tw=ctx.measureText(endLabel).width;
  ctx.fillText(endLabel,width-right-tw,height-6);
}

function showOfflineState() {
  $('freshness').textContent = lastSnapshot
    ? 'الاتصال متقطع · نعرض آخر بيانات مستلمة'
    : 'تعذر الاتصال بالخادم المحلي';
  $('live-dot').className = 'signal-dot bad';
}

async function loadSnapshot() {
  try {
    const response = await fetch('/api/mosul/live', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const snapshot = await response.json();
    retryDelay = 5000;
    render(snapshot);
    window.setTimeout(loadSnapshot,30000);
  } catch (error) {
    console.error(error);
    showOfflineState();
    retryDelay = Math.min(retryDelay * 1.5,30000);
    window.setTimeout(loadSnapshot,retryDelay);
  }
}

window.addEventListener('resize', () => {
  if (map) window.setTimeout(() => map.invalidateSize(),80);
  if (lastSnapshot) drawAirChart(sectionData(lastSnapshot,'air').hourly_24h || []);
});

tickClock();
window.setInterval(tickClock,1000);
initMap();
loadSnapshot();
window.setInterval(rotateScene,18000);
