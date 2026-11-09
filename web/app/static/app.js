async function api(path, opts={}) {
  const r = await fetch(path, opts);
  if (r.status === 401) { location.href = '/login'; throw new Error('auth'); }
  return r.json();
}

async function createJob() {
  const url = document.getElementById('newUrl').value.trim();
  const title = document.getElementById('newTitle').value.trim();
  if (!url) return;
  await api('/api/jobs', {method:'POST', headers:{'content-type':'application/json'},
                           body: JSON.stringify({url, title})});
  document.getElementById('newUrl').value = '';
  document.getElementById('newTitle').value = '';
  refresh();
}

async function refresh() {
  const tbody = document.querySelector('#jobs tbody');
  if (!tbody) return;
  const jobs = await api('/api/jobs');
  tbody.innerHTML = jobs.map(j => `
    <tr>
      <td><a href="/jobs/${j.id}">#${j.id}</a></td>
      <td>${(j.title||'').slice(0,60)}</td>
      <td>${j.status}</td>
      <td><div class="bar"><i style="width:${j.progress}%"></i></div>${j.progress}%</td>
      <td>${(j.message||'').slice(0,40)}</td>
      <td>
        <button onclick="retry(${j.id})">retry</button>
        <button onclick="cancel(${j.id})">cancel</button>
      </td>
    </tr>`).join('');
}

async function retry(id){ await api(`/api/jobs/${id}/retry`, {method:'POST'}); refresh(); }
async function cancel(id){ await api(`/api/jobs/${id}/cancel`, {method:'POST'}); refresh(); }

async function refreshJob() {
  const el = document.getElementById('job');
  if (!el) return;
  const id = el.dataset.id;
  const j = await api(`/api/jobs/${id}`);
  el.innerHTML = `
    <p><b>${j.title||''}</b> — ${j.status} ${j.progress}%</p>
    <p>${j.message||''}</p>
    ${j.output_url ? `<p>R2: <a href="${j.output_url}" target="_blank">${j.output_url}</a></p>` : ''}
    ${j.tg_file_id ? `<p>Telegram: ✅</p>` : ''}
    ${j.error ? `<p class="err">${j.error}</p>` : ''}
  `;
  document.getElementById('log').textContent = j.log || '';
}

async function saveSettings() {
  const form = document.getElementById('sform');
  const body = {};
  form.querySelectorAll('input').forEach(i => body[i.name] = i.value);
  await api('/api/settings', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(body)});
  alert('Saved');
}

async function loadSettings() {
  const form = document.getElementById('sform');
  if (!form) return;
  const s = await api('/api/settings');
  form.innerHTML = Object.entries(s).map(([k,v]) =>
    `<label>${k}<br><input name="${k}" value="${v||''}"></label><br>`).join('');
}

if (document.querySelector('#jobs')) { refresh(); setInterval(refresh, 3000); }
if (document.querySelector('#job'))   { refreshJob(); setInterval(refreshJob, 3000); }
if (document.querySelector('#sform')) loadSettings();