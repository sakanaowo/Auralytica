'use strict';
let metadataRun = null, metadataPoll = null, classificationPreview = null;
const metadataLabels = {pending:'Đang chờ',running:'Đang lấy metadata',stop_requested:'Đang dừng',paused:'Đã dừng',completed:'Hoàn tất',partial:'Có lỗi',failed:'Thất bại'};

async function loadMetadataScope() {
  if (pageName !== 'explore' || !workflow?.active_import) return;
  const params = new URLSearchParams({group:$('#metadata-group').value,limit:$('#metadata-limit').value});
  try {
    const scope = await api('/api/metadata/scope?' + params);
    $('#metadata-scope').textContent = `${scope.selected} / ${scope.available} video trong phạm vi · ${scope.cached} cache còn hạn · ${scope.stale} cache cũ.`;
    $('#metadata-start').disabled = batchActive || !scope.selected;
  } catch (error) {
    $('#metadata-scope').textContent = error.message;
    $('#metadata-start').disabled = true;
  }
}

async function loadMetadataPanel() {
  await loadMetadataScope();
  try {
    const runs = await api('/api/metadata/runs');
    if (runs.items.length) await renderMetadataRun(runs.items[0]);
  } catch (error) { $('#metadata-status').textContent = error.message; }
}

async function renderMetadataRun(run) {
  metadataRun = run;
  const done = run.counts.done || 0, failed = run.counts.failed || 0;
  $('#metadata-status').textContent = `${metadataLabels[run.status] || run.status} · ${done}/${run.total} xong · ${failed} lỗi.`;
  $('#metadata-stop').disabled = !['pending','running'].includes(run.status);
  $('#metadata-resume').disabled = batchActive || !['paused','partial','failed'].includes(run.status);
  const events = await api(`/api/metadata/runs/${run.run_id}/events`);
  $('#metadata-events').replaceChildren(...events.items.slice(0,20).map(item =>
    node('p',`${item.video_id || 'run'} · ${item.kind}${item.payload.error_code ? ' · '+item.payload.error_code : ''}`)));
  if (['pending','running','stop_requested'].includes(run.status)) {
    clearTimeout(metadataPoll);
    metadataPoll = setTimeout(pollMetadata,500);
  } else await loadMetadataScope();
}

async function pollMetadata() {
  if (!metadataRun) return;
  try { await renderMetadataRun(await api(`/api/metadata/runs/${metadataRun.run_id}`)); }
  catch (error) { $('#metadata-status').textContent = error.message; }
}

async function metadataCommand(command) {
  try {
    if (command === 'start') {
      metadataRun = await api('/api/metadata/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        group:$('#metadata-group').value,limit:Number($('#metadata-limit').value),refresh:$('#metadata-refresh').checked})});
    } else metadataRun = await api(`/api/metadata/runs/${metadataRun.run_id}/${command}`,{method:'POST'});
    await renderMetadataRun(metadataRun);
  } catch (error) { $('#metadata-status').textContent = error.message; }
}

function renderClassificationPreview(plan) {
  classificationPreview = plan;
  const changed = plan.items.filter(item => item.changed);
  $('#preview-summary').textContent = `${plan.changed} thay đổi / ${plan.items.length} video có metadata. Nhãn thủ công luôn được giữ.`;
  const body = $('#preview-items'); body.replaceChildren();
  for (const item of changed) {
    const row = node('tr'); row.append(node('td',item.title || item.video_id),
      node('td',`${item.current_group} → ${item.proposed_group}`),node('td',item.reason)); body.append(row);
  }
  $('#preview-table').hidden = !changed.length;
  $('#classification-apply').disabled = batchActive || !changed.length || plan.status === 'applied';
}

async function createClassificationPreview() {
  try { renderClassificationPreview(await api('/api/classification/previews',{method:'POST'})); }
  catch (error) { $('#preview-summary').textContent = error.message; }
}

async function applyClassificationPreview() {
  try {
    const result = await api(`/api/classification/previews/${classificationPreview.preview_id}/apply`,{method:'POST'});
    $('#preview-summary').textContent = `Đã áp dụng ${result.changed} thay đổi.`;
    $('#classification-apply').disabled = true;
    await loadWorkflow();
  } catch (error) { $('#preview-summary').textContent = error.message; }
}

if (pageName === 'explore') {
  $('#metadata-group').addEventListener('change',loadMetadataScope);
  $('#metadata-limit').addEventListener('input',loadMetadataScope);
  $('#metadata-start').addEventListener('click',() => metadataCommand('start'));
  $('#metadata-stop').addEventListener('click',() => metadataCommand('stop'));
  $('#metadata-resume').addEventListener('click',() => metadataCommand('resume'));
  $('#classification-preview').addEventListener('click',createClassificationPreview);
  $('#classification-apply').addEventListener('click',applyClassificationPreview);
}
