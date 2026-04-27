const params = new URLSearchParams(location.search);
const sessionId = params.get('id');
const video = document.getElementById('mainVideo');
const videoSrc = document.getElementById('videoSrc');

let allShots = [];
let sortKey = 'shot_number';
let sortAsc = true;
let charts = {};
let pollTimer = null;

const CHART_COLORS = {
  forehand:  '#60a5fa',
  backhand:  '#a78bfa',
  volley:    '#34d399',
  overhead:  '#fbbf24',
  unknown:   '#6b7280',
  topspin:   '#4ade80',
  underspin: '#f87171',
  flat:      '#94a3b8',
};

async function init() {
  if (!sessionId) { document.body.innerHTML = '<div class="empty-state">No session ID</div>'; return; }

  const session = await (await fetch(`/api/sessions/${sessionId}`)).json();
  document.getElementById('sessionTitle').textContent = session.filename;
  document.title = `Rally Coach — ${session.filename}`;

  if (session.status === 'complete') {
    videoSrc.src = `/api/sessions/${sessionId}/video`;
    video.load();
    await loadShots();
    updateKPIs(session);
  } else if (session.status === 'processing' || session.status === 'queued') {
    document.getElementById('kpiShots').textContent = session.status;
    pollTimer = setInterval(async () => {
      const s = await (await fetch(`/api/sessions/${sessionId}`)).json();
      if (s.status === 'complete') {
        clearInterval(pollTimer);
        location.reload();
      } else if (s.status === 'error') {
        clearInterval(pollTimer);
        document.getElementById('kpiShots').textContent = 'Error: ' + s.error_message;
      }
    }, 5000);
  } else if (session.status === 'error') {
    document.getElementById('kpiShots').textContent = 'Error: ' + session.error_message;
  }
}

function updateKPIs(session) {
  document.getElementById('kpiShots').textContent = session.total_shots || '0';
  document.getElementById('kpiSpeed').textContent = session.avg_speed_mph ? session.avg_speed_mph + ' mph' : '—';
}

async function loadShots() {
  const res = await fetch(`/api/sessions/${sessionId}/shots`);
  allShots = await res.json();

  if (!allShots.length) return;

  // Compute aggregate KPIs from shots
  const inShots = allShots.filter(s => s.is_in === 1).length;
  const netShots = allShots.filter(s => s.cleared_net === 1).length;
  document.getElementById('kpiInBounds').textContent = allShots.length
    ? Math.round(inShots / allShots.length * 100) + '%' : '—';
  document.getElementById('kpiNetClear').textContent = allShots.length
    ? Math.round(netShots / allShots.length * 100) + '%' : '—';

  renderShotTable();
  renderCharts();
  courtViz.setShots(allShots);
  courtViz.onClickShot = shot => seekToShot(shot);
}

function renderShotTable() {
  const sorted = [...allShots].sort((a, b) => {
    const va = a[sortKey] ?? 0;
    const vb = b[sortKey] ?? 0;
    return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });

  const rows = sorted.map(s => {
    const inClass = s.is_close_call ? 'in-close' : (s.is_in ? 'in-yes' : 'in-no');
    const inLabel = s.is_close_call ? 'Close' : (s.is_in ? 'In' : 'Out');
    return `<tr data-shotid="${s.shot_id}" onclick="seekToShot(window._shots['${s.shot_id}'])">
      <td>${s.shot_number}</td>
      <td>${s.start_time_sec != null ? s.start_time_sec.toFixed(1) + 's' : '—'}</td>
      <td>${s.shot_type || '—'}</td>
      <td>${s.spin_type || '—'}</td>
      <td>${s.speed_mph != null ? s.speed_mph.toFixed(0) + ' mph' : '—'}</td>
      <td>${s.rpm_estimate != null ? Math.round(s.rpm_estimate) : '—'}</td>
      <td>${s.net_clearance_inches != null ? s.net_clearance_inches.toFixed(1) : '—'}</td>
      <td class="${inClass}">${inLabel}</td>
      <td>${s.quality_score != null ? s.quality_score.toFixed(0) : '—'}</td>
    </tr>`;
  }).join('');

  document.getElementById('shotRows').innerHTML = rows;

  // Index shots by id for click lookup
  window._shots = {};
  allShots.forEach(s => { window._shots[s.shot_id] = s; });
}

function sortBy(key) {
  if (sortKey === key) sortAsc = !sortAsc;
  else { sortKey = key; sortAsc = true; }
  renderShotTable();
}

function seekToShot(shot) {
  if (!shot) return;
  video.currentTime = shot.start_time_sec || 0;
  video.play();

  // Highlight row
  document.querySelectorAll('.shot-table tr.active').forEach(r => r.classList.remove('active'));
  const row = document.querySelector(`tr[data-shotid="${shot.shot_id}"]`);
  if (row) { row.classList.add('active'); row.scrollIntoView({ block: 'nearest' }); }
}

function renderCharts() {
  const shotTypeCounts = {};
  const spinTypeCounts = {};
  const speeds = [];
  const qualities = [];

  allShots.forEach(s => {
    shotTypeCounts[s.shot_type || 'unknown'] = (shotTypeCounts[s.shot_type || 'unknown'] || 0) + 1;
    spinTypeCounts[s.spin_type || 'unknown'] = (spinTypeCounts[s.spin_type || 'unknown'] || 0) + 1;
    if (s.speed_mph != null) speeds.push(s.speed_mph);
    if (s.quality_score != null) qualities.push(s.quality_score);
  });

  _doughnutChart('chartShotType', shotTypeCounts, CHART_COLORS);
  _barChart('chartSpinType', spinTypeCounts, CHART_COLORS);
  _histChart('chartSpeed', speeds, 'Speed (mph)', '#60a5fa', 10);
  _histChart('chartQuality', qualities, 'Quality', '#4ade80', 10);
}

function _doughnutChart(id, counts, colors) {
  const labels = Object.keys(counts);
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: labels.map(l => counts[l]), backgroundColor: labels.map(l => colors[l] || '#6b7280'), borderWidth: 0 }],
    },
    options: { plugins: { legend: { labels: { color: '#e2e8f0', font: { size: 11 } } } }, cutout: '60%' },
  });
}

function _barChart(id, counts, colors) {
  const labels = Object.keys(counts);
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: labels.map(l => counts[l]), backgroundColor: labels.map(l => colors[l] || '#6b7280'), borderRadius: 4, borderWidth: 0 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#8892a4' } }, y: { ticks: { color: '#8892a4' }, grid: { color: '#2d3347' } } } },
  });
}

function _histChart(id, data, label, color, bins) {
  if (!data.length) return;
  const min = Math.floor(Math.min(...data));
  const max = Math.ceil(Math.max(...data));
  const binSize = Math.max(1, Math.round((max - min) / bins));
  const buckets = {};
  for (let i = min; i <= max; i += binSize) buckets[i] = 0;
  data.forEach(v => {
    const bucket = Math.floor((v - min) / binSize) * binSize + min;
    if (buckets[bucket] !== undefined) buckets[bucket]++;
    else buckets[bucket] = 1;
  });
  const labels = Object.keys(buckets).map(Number).sort((a, b) => a - b);
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), {
    type: 'bar',
    data: {
      labels: labels.map(l => `${l}-${l + binSize}`),
      datasets: [{ data: labels.map(l => buckets[l]), backgroundColor: color + 'bb', borderRadius: 3, borderWidth: 0 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#8892a4', font: { size: 10 } } }, y: { ticks: { color: '#8892a4' }, grid: { color: '#2d3347' } } } },
  });
}

function exportCsv() {
  window.open(`/api/sessions/${sessionId}/shots/csv`);
}

init();
