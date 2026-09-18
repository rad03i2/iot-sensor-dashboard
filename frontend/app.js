const $ = id => document.getElementById(id);
const MOSUL = [36.335, 43.118889];
let map, airCircle, cityMarker;
let lastSnapshot = null;

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

function aqiLabel(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return 'غير متاح';
  if (v <= 50) return 'جيد';
  if (v <= 100) return 'متوسط';
  if (v <= 150) return 'غير صحي للحساسين';
  if (v <= 200) return 'غير صحي';
  if (v <= 300) return 'غير صحي جداً';
  return 'خطر';
}

function aqiColor(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return '#6f8b82';
  if (v <= 50) return '#46e6a1';
  if (v <= 100) return '#f5d86e';
  if (v <= 150) return '#ffab62';
  if (v <= 200) return '#ff6d78';
  return '#c17bff';
}

function initMap() {
  map = L.map('map', {zoomControl:false, attributionControl:true}).setView(MOSUL, 11.5);
  L.control.zoom({position:'bottomleft'}).addTo(map);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom:19,
    attribution:'© OpenStreetMap'
  }).addTo(map);

  cityMarker = L.marker(MOSUL).addTo(map).bindPopup('الموصل · مركز العرض البيئي');
  airCircle = L.circle(MOSUL, {
    radius: 8500, color:'#46e6a1', fillColor:'#46e6a1', fillOpacity:.18, weight:2
  }).addTo(map);
  setTimeout(() => map.invalidateSize(), 100);
}

function tickClock() {
  const now = new Date();
  $('clock').textContent = new Intl.DateTimeFormat('ar-IQ', {
    timeZone:'Asia/Baghdad', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false
  }).format(now);
  $('date').textContent = new Intl.DateTimeFormat('ar-IQ', {
    timeZone:'Asia/Baghdad', weekday:'long', year:'numeric', month:'long', day:'numeric'
  }).format(now);
}

function sectionData(snapshot, key) {
  return (snapshot && snapshot[key] && snapshot[key].data) || {};
}

function render(snapshot) {
  lastSnapshot = snapshot;
  const weatherSection = snapshot.weather || {};
  const airSection = snapshot.air || {};
  const riverSection = snapshot.river || {};
  const weather = sectionData(snapshot,'weather');
  const air = sectionData(snapshot,'air');
  const river = sectionData(snapshot,'river');
  const wc = weather.current || {};
  const ac = air.current || {};
  const rc = river.current || {};

  $('k-temp').textContent = num(wc.temperature_c,1) + '°';
  $('k-humidity').textContent = num(wc.humidity_pct) + '%';
  $('k-pm25').textContent = num(ac.pm25_ug_m3,1);
  $('k-pm10').textContent = num(ac.pm10_ug_m3,1);
  $('k-aqi').textContent = num(ac.us_aqi);
  $('k-aqi-label').textContent = aqiLabel(ac.us_aqi) + ' · CAMS';
  $('k-aqi').style.color = aqiColor(ac.us_aqi);
  $('k-dust').textContent = num(ac.dust_ug_m3,1);
  $('k-uv').textContent = num(ac.uv_index,1);
  $('k-river').textContent = rc.river_discharge_m3_s == null ? '--' : num(rc.river_discharge_m3_s,1);

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
    ? (change >= 0 ? '▲ ' : '▼ ') + Math.abs(change).toFixed(1) + '% عن اليوم السابق'
    : 'لا توجد مقارنة يومية';
  $('river-trend').className = Number.isFinite(change)
    ? (change >= 0 ? 'up' : 'down') : '';

  $('brief').textContent = snapshot.brief_ar || 'بانتظار البيانات.';
  renderAlerts(snapshot.alerts || []);
  renderSources(snapshot);
  renderForecast(weather.daily_5d || []);
  drawAirChart(air.hourly_24h || []);
  renderFreshness(snapshot);

  if (airCircle) {
    const color = aqiColor(ac.us_aqi);
    airCircle.setStyle({color:color, fillColor:color});
    airCircle.bindPopup(
      '<div class="map-pop"><b>الموصل · CAMS Global</b><br>US AQI: ' +
      num(ac.us_aqi) + ' (' + aqiLabel(ac.us_aqi) + ')<br>PM2.5: ' +
      num(ac.pm25_ug_m3,1) + ' µg/m³<br><small>نموذج جوي، ليس حساساً أرضياً.</small></div>'
    );
  }

  const allBad = [weatherSection, airSection, riverSection].every(
    s => s.status === 'unavailable'
  );
  if (allBad) $('live-dot').className = 'bad';
}

function renderAlerts(alerts) {
  $('alerts').innerHTML = alerts.slice(0,3).map(a =>
    '<div class="alert ' + (a.severity || 'info') + '">' +
      '<span>' + (a.icon || '●') + '</span>' +
      '<div><b>' + a.title + '</b><small>' + a.message + '</small></div>' +
    '</div>'
  ).join('') || '<div class="alert info"><span>●</span><div><b>لا توجد تنبيهات</b></div></div>';
}

function renderSources(snapshot) {
  const items = [
    ['الطقس', snapshot.weather],
    ['الهواء', snapshot.air],
    ['دجلة', snapshot.river]
  ];
  $('source-status').innerHTML = items.map(item => {
    const label = item[0], section = item[1] || {};
    const status = section.status || 'unavailable';
    const text = status === 'ok' ? 'متصل' : status === 'stale' ? 'آخر بيانات محفوظة' : 'غير متاح';
    return '<div><span><i class="' + status + '"></i>' + label +
      '</span><b>' + text + '</b></div>';
  }).join('');
}

function renderForecast(days) {
  $('forecast').innerHTML = days.slice(0,5).map(day => {
    const date = day.date ? new Date(day.date + 'T12:00:00') : null;
    const name = date ? new Intl.DateTimeFormat('ar-IQ',{weekday:'short'}).format(date) : '--';
    return '<div class="forecast-day">' +
      '<b>' + name + '</b>' +
      '<span>' + (weatherText[day.weather_code] || '—') + '</span>' +
      '<strong>' + num(day.temperature_max_c) + '°</strong>' +
      '<small>' + num(day.temperature_min_c) + '° · مطر ' +
      num(day.precipitation_probability_max_pct) + '%</small></div>';
  }).join('') || '<div class="empty">التوقعات غير متاحة مؤقتاً</div>';
}

function renderFreshness(snapshot) {
  const refresh = snapshot.last_refresh ? new Date(snapshot.last_refresh) : null;
  if (!refresh || Number.isNaN(refresh.getTime())) {
    $('freshness').textContent = 'بانتظار أول تحديث';
    $('last-refresh').textContent = 'آخر تحديث: --';
    return;
  }
  const ageMin = Math.max(0, Math.round((Date.now() - refresh.getTime()) / 60000));
  $('freshness').textContent = ageMin <= 10 ? 'المرصد متصل' : 'آخر تحديث منذ ' + ageMin + ' دقيقة';
  $('last-refresh').textContent = 'آخر تحديث: ' + new Intl.DateTimeFormat('ar-IQ',{
    timeZone:'Asia/Baghdad',hour:'2-digit',minute:'2-digit',hour12:false
  }).format(refresh);
  $('live-dot').className = ageMin > 20 ? 'warn' : '';
}

function drawAirChart(rows) {
  const canvas = $('air-chart');
  const box = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(360, Math.floor(box.width));
  const h = Math.max(115, Math.floor(box.height || 125));
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,w,h);

  const points = rows.filter(r =>
    Number.isFinite(Number(r.pm25_ug_m3)) || Number.isFinite(Number(r.dust_ug_m3))
  );
  if (points.length < 2) {
    ctx.fillStyle='#78958b';
    ctx.font='12px system-ui';
    ctx.fillText('لا تتوفر سلسلة 24 ساعة حالياً',14,28);
    return;
  }
  const all = points.flatMap(r => [Number(r.pm25_ug_m3)||0, Number(r.dust_ug_m3)||0]);
  const max = Math.max(10,...all) * 1.12;
  const left=30,right=8,top=8,bottom=22,pw=w-left-right,ph=h-top-bottom;

  ctx.strokeStyle='rgba(159,203,187,.12)';
  ctx.lineWidth=1;
  for(let i=0;i<4;i++){
    const y=top+ph*i/3;
    ctx.beginPath();
    ctx.moveTo(left,y);
    ctx.lineTo(w-right,y);
    ctx.stroke();
  }

  function line(key,color){
    ctx.beginPath();
    points.forEach((p,i)=>{
      const x=left+(i/(points.length-1))*pw;
      const v=Number(p[key])||0;
      const y=top+ph-(v/max)*ph;
      if(i) ctx.lineTo(x,y); else ctx.moveTo(x,y);
    });
    ctx.strokeStyle=color;
    ctx.lineWidth=2;
    ctx.stroke();
  }
  line('dust_ug_m3','#d6a667');
  line('pm25_ug_m3','#58e6b0');

  ctx.fillStyle='#78958b';
  ctx.font='10px system-ui';
  const first=points[0], last=points[points.length-1];
  const fmt = t => t ? new Date(t).toLocaleTimeString('ar-IQ',{hour:'2-digit',minute:'2-digit'}) : '--';
  ctx.fillText(fmt(first.time),left,h-6);
  const end=fmt(last.time);
  const tw=ctx.measureText(end).width;
  ctx.fillText(end,w-right-tw,h-6);
}

async function loadSnapshot() {
  try {
    const response = await fetch('/api/mosul/live', {cache:'no-store'});
    if (!response.ok) throw new Error('HTTP ' + response.status);
    render(await response.json());
  } catch (error) {
    console.error(error);
    $('freshness').textContent = 'تعذر الاتصال بالخادم المحلي';
    $('live-dot').className = 'bad';
  }
}

window.addEventListener('resize', () => {
  if (map) setTimeout(()=>map.invalidateSize(),80);
  if (lastSnapshot) drawAirChart(sectionData(lastSnapshot,'air').hourly_24h || []);
});

tickClock();
setInterval(tickClock,1000);
initMap();
loadSnapshot();
setInterval(loadSnapshot,30000);
