const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const uploadMsg = document.getElementById('uploadMsg');
const progressFill = document.getElementById('progressFill');

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) uploadFile(fileInput.files[0]); });

function uploadFile(file) {
  const form = new FormData();
  form.append('file', file);

  uploadStatus.style.display = 'block';
  uploadMsg.textContent = `Uploading ${file.name}…`;
  progressFill.style.width = '0%';

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/sessions');

  xhr.upload.onprogress = e => {
    if (e.lengthComputable) {
      progressFill.style.width = `${Math.round(e.loaded / e.total * 100)}%`;
    }
  };

  xhr.onload = () => {
    if (xhr.status === 201) {
      const data = JSON.parse(xhr.responseText);
      uploadMsg.textContent = `Upload complete — processing session ${data.session_id.slice(0,8)}…`;
      progressFill.style.width = '100%';
      loadSessions();
      startPolling(data.session_id);
    } else {
      uploadMsg.textContent = `Upload failed: ${xhr.responseText}`;
      uploadMsg.style.color = 'var(--danger)';
    }
  };
  xhr.onerror = () => { uploadMsg.textContent = 'Network error'; };
  xhr.send(form);
}

async function loadSessions() {
  const res = await fetch('/api/sessions');
  const sessions = await res.json();
  const container = document.getElementById('sessionsContainer');

  if (!sessions.length) {
    container.innerHTML = '<div class="empty-state">No sessions yet. Upload a video to get started.</div>';
    return;
  }

  const rows = sessions.map(s => `
    <tr>
      <td><a href="/session?id=${s.session_id}">${s.filename}</a></td>
      <td>${new Date(s.uploaded_at).toLocaleString()}</td>
      <td><span class="badge badge-${s.status}">${s.status}</span></td>
      <td>${s.total_shots || '—'}</td>
      <td>${s.avg_speed_mph ? s.avg_speed_mph + ' mph' : '—'}</td>
      <td>${s.avg_quality_score ? s.avg_quality_score : '—'}</td>
      <td>
        ${s.status === 'complete'
          ? `<a href="/session?id=${s.session_id}" class="btn btn-primary btn-sm">View</a>`
          : `<span style="color:var(--muted);font-size:12px;">${s.status}</span>`}
      </td>
    </tr>
  `).join('');

  container.innerHTML = `
    <table class="sessions-table">
      <thead>
        <tr>
          <th>File</th><th>Uploaded</th><th>Status</th>
          <th>Shots</th><th>Avg Speed</th><th>Avg Quality</th><th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

const pollers = {};
function startPolling(sessionId) {
  if (pollers[sessionId]) return;
  pollers[sessionId] = setInterval(async () => {
    const res = await fetch(`/api/sessions/${sessionId}`);
    const s = await res.json();
    if (s.status === 'complete' || s.status === 'error') {
      clearInterval(pollers[sessionId]);
      delete pollers[sessionId];
      loadSessions();
    }
  }, 4000);
}

loadSessions();
setInterval(loadSessions, 10000);
