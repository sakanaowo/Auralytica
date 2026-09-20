'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const reasons = {ytmusic_strong:'Metadata YouTube Music',ytmusic_ugc_recurrence:'YouTube Music · xem lại nhiều ngày',manual:'Đã chuyển tay',topic_channel:'Kênh Topic',music_library:'Music library',music_hint:'Có dấu hiệu nhạc · cần duyệt',unknown:'Chưa rõ',talk_context:'Ngữ cảnh nói chuyện · cần duyệt',conflicting_evidence:'Bằng chứng mâu thuẫn',shorts_url:'YouTube Shorts',channel_decision:'Theo nhãn kênh'};
const pageName = location.pathname.slice(1);
const groups = {};
let workflow = null;
let busy = false;
let batchActive = false;
let candidates = [];
function notice(text, error = false) { $('#notice').textContent = text; $('#notice').classList.toggle('error', error); }
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
async function api(url, options) {
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); } catch { throw new Error('Server trả kết quả không hợp lệ. Thử tải lại trang.'); }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Dữ liệu gửi chưa hợp lệ. Kiểm tra và thử lại.');
  return data;
}
function controls(s) {
  const locked = busy || batchActive || s.loading;
  $('.bulk-move',s.el).disabled = locked || !s.selected.size;
  $('.bulk-move',s.el).textContent = `${s.name === 'music' ? 'Sang Còn lại →' : '← Sang Nhạc'} (${s.selected.size})`;
  const all = $('.select-page',s.el);
  all.disabled = locked || !s.items.length;
  all.checked = !!s.items.length && s.selected.size === s.items.length;
  all.indeterminate = !!s.selected.size && s.selected.size < s.items.length;
  s.el.querySelectorAll('tbody input, .row-move').forEach(el => { el.disabled = locked; });
  $('.prev',s.el).disabled = busy || s.loading || s.page <= 1;
  $('.next',s.el).disabled = busy || s.loading || s.page >= Math.max(1,Math.ceil(s.count/s.pageSize));
}
function lock(value) { busy = value; $('#choose-folder').disabled = value || batchActive; for (const s of Object.values(groups)) controls(s); }
function render(s) {
  const tbody = $('tbody',s.el); tbody.replaceChildren();
  for (const item of s.items) {
    const tr = node('tr'); const checkCell = node('td'); const check = node('input');
    check.type = 'checkbox'; check.setAttribute('aria-label',`Chọn ${item.title || item.id}`);
    check.addEventListener('change', () => { check.checked ? s.selected.add(item.id) : s.selected.delete(item.id); controls(s); });
    checkCell.append(check); tr.append(checkCell);
    const cell = node('td'); const content = node('div',undefined,'video-cell');
    const thumb = node('div','♪','thumbnail'); thumb.setAttribute('aria-label','Ảnh xem trước');
    if (/^[A-Za-z0-9_-]{11}$/.test(item.id)) {
      const img = node('img'); img.alt = ''; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer';
      img.addEventListener('error', () => { img.remove(); thumb.textContent = '♪'; });
      img.src = `https://i.ytimg.com/vi/${item.id}/mqdefault.jpg`; thumb.replaceChildren(img);
    }
    const info = node('div',undefined,'video-info'); const link = node('a',item.title || item.id);
    link.href = `https://www.youtube.com/watch?v=${encodeURIComponent(item.id)}`; link.target = '_blank'; link.rel = 'noopener noreferrer';
    info.append(link,node('div',item.channel_name || 'Chưa có thông tin kênh','channel-name'));
    const label = node('div',reasons[item.reason] || item.reason,'reason-label');
    label.classList.toggle('manual',item.decision_source === 'user');
    label.title = item.evidence.map(e => `${e.code} · ${e.source}`).join('\n'); info.append(label);
    if (item.download_status) info.append(node('div',`Trạng thái tải: ${item.download_status}`,'download-status'));
    content.append(thumb,info); cell.append(content); tr.append(cell,node('td',String(item.watch_count)));
    const action = node('td'); const move = node('button',s.name === 'music' ? '→' : '←','row-move');
    move.setAttribute('aria-label',`Chuyển ${item.title || item.id} sang ${s.name === 'music' ? 'Còn lại' : 'Nhạc'}`);
    move.addEventListener('click',() => moveItems(s,[item.id])); action.append(move); tr.append(action); tbody.append(tr);
  }
  const empty = $('.empty',s.el); empty.hidden = !!s.items.length;
  empty.textContent = 'Không có video phù hợp. Thử đổi bộ lọc hoặc nhập folder Takeout.';
  $('.results',s.el).textContent = `${s.count.toLocaleString('vi-VN')} video khớp bộ lọc`;
  $('.page-label',s.el).textContent = `${s.page} / ${Math.max(1,Math.ceil(s.count/s.pageSize))}`;
  controls(s);
}
async function load(s) {
  $('.list-retry',s.el).hidden = true;
  $('.results',s.el).textContent = 'Đang tải…';
  const revision = ++s.revision; s.loading = true; s.selected.clear(); controls(s);
  const params = new URLSearchParams({group:s.name,search:$('.search',s.el).value,sort:$('.sort',s.el).value,page:s.page,page_size:s.pageSize});
  const channel = $('.channel',s.el).value.trim(); if (channel) params.set('channel',channel);
  const reason = $('.reason',s.el).value; if (reason) params.set('reason',reason);
  try {
    const data = await api(`/api/videos?${params}`);
    if (revision !== s.revision) return;
    s.count = data.filtered_count;
    const maxPage = Math.max(1,Math.ceil(s.count/s.pageSize));
    if (s.page > maxPage) { s.page = maxPage; saveExplore(false); return load(s); }
    s.items = data.items;
    for (const name of ['music','rest']) $(`#${name}-total`).textContent = String(data.group_totals[name]);
    s.loading = false; render(s);
  } catch (error) {
    if (revision !== s.revision) return;
    s.loading = false; s.items = []; s.count = 0; render(s);
    $('.empty',s.el).textContent = error.message;
    $('.list-retry',s.el).hidden = false;
    notice(error.message,true);
  }
}
async function refresh() {
  if (pageName === 'explore') await Promise.all([load(groups.music), ...(!$('#rest').hidden ? [load(groups.rest)] : []), loadSummary()]);
  if (pageName === 'download') await updatePreview();
}
async function moveItems(s, ids) {
  if (busy || batchActive || s.loading || !ids.length) return;
  lock(true);
  try {
    await api('/api/videos/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video_ids:ids,to_group:s.name === 'music' ? 'rest' : 'music'})});
    await refresh(); notice(`Đã chuyển ${ids.length} video. Lựa chọn đã được lưu.`);
  } catch (error) { notice(error.message,true); }
  finally { lock(false); }
}
for (const name of pageName === 'explore' ? ['music','rest'] : []) {
  const el = $(`#${name}`); el.append($('#panel-template').content.cloneNode(true));
  const s = {name,el,page:1,pageSize:50,count:0,items:[],selected:new Set(),loading:false,revision:0}; groups[name] = s;
  let timer;
  for (const field of ['.search','.channel']) $(field,el).addEventListener('input',() => {
    clearTimeout(timer); s.selected.clear(); s.loading = true; ++s.revision; controls(s); s.page = 1;
    timer = setTimeout(() => { saveExplore(); load(s); },200);
    s.cancelSearch = () => clearTimeout(timer);
  });
  for (const selector of ['.reason','.sort']) $(selector,el).addEventListener('change',() => { s.page = 1; saveExplore(); load(s); });
  $('.page-size',el).addEventListener('change',() => { s.pageSize = Number($('.page-size',el).value); s.page = 1; saveExplore(); load(s); });
  $('.prev',el).addEventListener('click',() => { --s.page; saveExplore(); load(s); });
  $('.next',el).addEventListener('click',() => { ++s.page; saveExplore(); load(s); });
  $('.select-page',el).addEventListener('change',event => {
    s.selected = new Set(event.target.checked ? s.items.map(i => i.id) : []);
    el.querySelectorAll('tbody input').forEach(input => { input.checked = event.target.checked; }); controls(s);
  });
  $('.list-retry',el).addEventListener('click',() => load(s));
  $('.bulk-move',el).addEventListener('click',() => moveItems(s,[...s.selected]));
}

function libraryFor(history) {
  const slash = history.path.lastIndexOf('/');
  let base = history.path.slice(0,slash+1);
  if (base.endsWith('history/')) base = base.slice(0,-8);
  return candidates.filter(item => item.file.name === 'music library songs.csv' && item.path.startsWith(base));
}
function updateLibrary() {
  const history = candidates[Number($('#history-source').value)]; const select = $('#library-source');
  select.replaceChildren(new Option('Không dùng music library',''));
  const libraries = libraryFor(history);
  for (const item of libraries) select.add(new Option(item.path,String(candidates.indexOf(item))));
  if (libraries.length === 1) select.value = String(candidates.indexOf(libraries[0]));
}
async function importFiles(history, library) {
  lock(true); notice('Đang nhập và nhận dạng video…');
  try {
    const data = new FormData(); data.append('files',history.file,'watch-history.json');
    if (library) data.append('files',library.file,'music library songs.csv');
    if (history.file.size + (library?.file.size || 0) > 63*1024*1024) throw new Error('Dữ liệu vượt giới hạn upload 63 MiB của bản local hiện tại.');
    await api('/api/imports',{method:'POST',body:data});
    location.assign('/explore');
  } catch (error) { notice(error.message,true); }
  finally { lock(false); $('#folder-input').value = ''; }
}
async function chooseFiles(files) {
  if (busy || batchActive) return;
  candidates = files.filter(item => ['watch-history.json','music library songs.csv'].includes(item.file.name));
  const histories = candidates.filter(item => item.file.name === 'watch-history.json');
  if (!histories.length) { notice('Không tìm thấy watch-history.json. Hãy chọn folder Takeout đã giải nén có lịch sử JSON; HTML chưa hỗ trợ.',true); $('#folder-input').value = ''; return; }
  if (histories.length === 1 && libraryFor(histories[0]).length <= 1) return importFiles(histories[0],libraryFor(histories[0])[0]);
  $('#history-source').replaceChildren();
  for (const item of histories) $('#history-source').add(new Option(item.path,String(candidates.indexOf(item))));
  updateLibrary(); $('#source-dialog').showModal();
}
$('#history-source').addEventListener('change',updateLibrary);
$('#source-dialog').addEventListener('close',() => {
  if ($('#source-dialog').returnValue === 'import') {
    const library = $('#library-source').value;
    importFiles(candidates[Number($('#history-source').value)],library === '' ? null : candidates[Number(library)]);
  } else $('#folder-input').value = '';
});
$('#choose-folder').addEventListener('click',() => $('#folder-input').click());
$('#folder-input').addEventListener('change',event => chooseFiles([...event.target.files].map(file => ({file,path:file.webkitRelativePath || file.name}))));
async function readEntry(entry) {
  if (entry.isFile) {
    if (!['watch-history.json','music library songs.csv'].includes(entry.name)) return [];
    const file = await new Promise((resolve,reject) => entry.file(resolve,reject));
    return [{file,path:entry.fullPath.replace(/^\//,'')}];
  }
  const reader = entry.createReader(); const files = [];
  while (true) {
    const entries = await new Promise((resolve,reject) => reader.readEntries(resolve,reject));
    if (!entries.length) break;
    for (const child of entries) files.push(...await readEntry(child));
  }
  return files;
}
const zone = $('#dropzone');
zone.addEventListener('dragover',event => { event.preventDefault(); if (!busy && !batchActive) zone.classList.add('dragging'); });
zone.addEventListener('dragleave',() => zone.classList.remove('dragging'));
zone.addEventListener('drop',async event => {
  event.preventDefault(); zone.classList.remove('dragging'); if (busy || batchActive) return;
  // Capture handles synchronously while the drop event's data store is readable.
  const entries = [...event.dataTransfer.items].map(item => item.webkitGetAsEntry?.()).filter(Boolean);
  const fallback = [...event.dataTransfer.files];
  try { await chooseFiles(entries.length ? (await Promise.all(entries.map(readEntry))).flat() : fallback.map(file => ({file,path:file.name}))); }
  catch (error) { notice(`Không đọc được folder: ${error.message}. Thử nút Chọn folder.`,true); }
});

const statuses = {queued:'Đang chờ',running:'Đang tải',paused:'Đã dừng',completed:'Hoàn tất',partial:'Có lỗi',failed:'Thất bại',skipped:'Đã có file',cancelled:'Đã hủy'};
let selectedBatch = null, batchPage = 1, currentBatch = null, downloadAction = false;
let previewNeeded = 0, previewToken = null, previewRevision = 0, polling = false;
function downloadControls() {
  $('#download-all').disabled = busy || batchActive || downloadAction || previewNeeded <= 0;
  $('#output-dir').disabled = batchActive || downloadAction;
  $('#stop-download').disabled = downloadAction || !['queued','running'].includes(currentBatch?.status);
  $('#resume-download').disabled = downloadAction || batchActive || !['paused','partial','failed','cancelled'].includes(currentBatch?.status);
  lock(busy);
}
async function updatePreview() {
  const revision = ++previewRevision;
  previewNeeded = 0; previewToken = null; downloadControls();
  const output = $('#output-dir').value.trim();
  if (!output) { $('#download-preview').textContent = 'Nhập thư mục lưu để tải.'; return; }
  try {
    const data = await api('/api/downloads/preview?' + new URLSearchParams({output_dir:output}));
    if (revision !== previewRevision) return;
    previewNeeded = data.needed;
    previewToken = data.token;
    $('#download-preview').textContent = `${data.music} video nhạc · ${data.excluded} loại bởi Deduplicate · ${data.kept} giữ lại · ${data.skipped} file đã có · ${data.needed} file cần tải`;
  } catch (error) { if (revision === previewRevision) $('#download-preview').textContent = error.message; }
  downloadControls();
}
function renderBatch(batch) {
  currentBatch = batch;
  $('#batch-details').hidden = !batch;
  if (!batch) return;
  const done = (batch.counts.completed || 0) + (batch.counts.skipped || 0);
  $('#batch-summary').textContent = `Lượt #${batch.batch_id} · ${statuses[batch.status]} · ${batch.total} video · ${done} xong / ${batch.counts.failed || 0} lỗi${batch.stop_requested && batch.status === 'running' ? ' · Đang yêu cầu dừng…' : ''}`;
  $('#batch-output').textContent = batch.output_dir;
  $('#batch-progress').max = Math.max(1,batch.total); $('#batch-progress').value = done;
  $('#batch-error').textContent = batch.error || '';
  const body = $('#download-items'); body.replaceChildren();
  for (const item of batch.items) {
    const tr = node('tr'); const title = node('td'); const link = node('a',item.title || item.video_id);
    link.href = `https://www.youtube.com/watch?v=${encodeURIComponent(item.video_id)}`; link.target = '_blank'; link.rel = 'noopener noreferrer'; title.append(link);
    let progress = statuses[item.status];
    if (item.status === 'running') progress += ` · ${item.downloaded_bytes.toLocaleString('vi-VN')} / ${item.total_bytes?.toLocaleString('vi-VN') || '?'} byte`;
    tr.append(title,node('td',progress),node('td',item.error_message || '')); body.append(tr);
  }
  const pages = Math.max(1,Math.ceil(batch.total/20));
  $('#batch-page').textContent = `${batchPage} / ${pages}`;
  $('#batch-prev').disabled = batchPage <= 1; $('#batch-next').disabled = batchPage >= pages;
}
async function pollDownloads() {
  if (polling) return;
  polling = true;
  try {
    const data = await api('/api/downloads');
    const wasActive = batchActive;
    batchActive = data.batches.some(b => ['queued','running'].includes(b.status));
    if (!data.batches.some(b => b.batch_id === selectedBatch)) selectedBatch = data.batches[0]?.batch_id || null;
    const select = $('#batch-select'); select.replaceChildren();
    for (const b of data.batches) select.add(new Option(`#${b.batch_id} · ${statuses[b.status]} · ${b.total} video`,String(b.batch_id)));
    if (selectedBatch) select.value = String(selectedBatch);
    const requested = selectedBatch, requestedPage = batchPage;
    const batch = requested ? await api(`/api/downloads/${requested}?page=${requestedPage}&page_size=20`) : null;
    if (selectedBatch === requested && batchPage === requestedPage) renderBatch(batch);
    $('#download-error').textContent = '';
    if (wasActive && !batchActive) await refresh();
    else await updatePreview();
  } catch (error) { $('#download-error').textContent = error.message; }
  finally { polling = false; downloadControls(); }
}
async function downloadCommand(action) {
  if (downloadAction) return;
  downloadAction = true; downloadControls();
  try {
    const options = {method:'POST',headers:{'Content-Type':'application/json'}};
    const url = action === 'start' ? '/api/downloads' : `/api/downloads/${selectedBatch}/${action}`;
    if (action === 'start') options.body = JSON.stringify({output_dir:$('#output-dir').value.trim(),preview_token:previewToken});
    const data = await api(url,options);
    selectedBatch = data.batch_id; batchPage = 1;
    batchActive = ['queued','running'].includes(data.status);
    await pollDownloads();
  } catch (error) { notice(error.message,true); if (action === 'start') await updatePreview(); }
  finally { downloadAction = false; downloadControls(); }
}
$('#download-all').addEventListener('click',() => downloadCommand('start'));
$('#stop-download').addEventListener('click',() => downloadCommand('stop'));
$('#resume-download').addEventListener('click',() => downloadCommand('resume'));
$('#batch-select').addEventListener('change',event => { selectedBatch = Number(event.target.value); batchPage = 1; pollDownloads(); });
$('#batch-prev').addEventListener('click',() => { --batchPage; pollDownloads(); });
$('#batch-next').addEventListener('click',() => { ++batchPage; pollDownloads(); });
let outputTimer;
try { $('#output-dir').value = localStorage.getItem('auralytica-output') || $('#output-dir').value; } catch {}
$('#output-dir').addEventListener('input',() => {
  ++previewRevision; previewNeeded = 0; previewToken = null; downloadControls(); clearTimeout(outputTimer);
  try { localStorage.setItem('auralytica-output',$('#output-dir').value); } catch {}
  outputTimer = setTimeout(updatePreview,250);
});
