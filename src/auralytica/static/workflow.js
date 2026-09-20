'use strict';
// Native page links handle navigation; only Explore stores filters in history.
function saveExplore(push = true) {
  const params = new URLSearchParams();
  if (!$('#rest').hidden) params.set('rest_open','1');
  for (const s of Object.values(groups)) {
    if (s.pageSize !== 50) params.set(`${s.name}_size`,s.pageSize);
    if (s.page > 1) params.set(`${s.name}_page`, s.page);
    for (const key of ['search','channel','reason','sort']) {
      const value = $(`.${key}`,s.el).value;
      if (value && !(key === 'sort' && value === 'watch_count')) params.set(`${s.name}_${key}`,value);
    }
  }
  const url = '/explore' + (params.size ? '?' + params : '');
  if (url !== location.pathname + location.search) history[push ? 'pushState' : 'replaceState'](null,'',url);
}
function restoreExplore() {
  const params = new URLSearchParams(location.search);
  setRestOpen(params.get('rest_open') === '1');
  for (const s of Object.values(groups)) {
    const size = Number(params.get(`${s.name}_size`) || 50);
    s.pageSize = [25,50,100].includes(size) ? size : 50;
    $('.page-size',s.el).value = String(s.pageSize);
    s.cancelSearch?.();
    const page = Number(params.get(`${s.name}_page`) || 1);
    s.page = Number.isSafeInteger(page) && page > 0 ? page : 1;
    for (const key of ['search','channel','reason','sort']) {
      const field = $(`.${key}`,s.el);
      field.value = (params.get(`${s.name}_${key}`) || (key === 'sort' ? 'watch_count' : '')).slice(0,500);
      if (key === 'sort' && !field.value) field.value = 'watch_count';
    }
  }
}
window.addEventListener('popstate',() => { if (pageName === 'explore') { restoreExplore(); refresh(); } });
const pageCopy = {
  import: ['Import · Nhập lịch sử', 'Chọn folder Google Takeout đã giải nén để bắt đầu hoặc đổi nguồn lịch sử.'],
  explore: ['Explore · Khám phá thư viện', 'Duyệt nhạc đã nhận dạng và chuyển video qua lại để sửa danh sách.'],
  deduplicate: ['Deduplicate · Chọn bản của cùng bài', 'So sánh các video có thể cùng bài trước khi tải.'],
  download: ['Download · Tải thư viện', 'Tải toàn bộ danh sách nhạc và theo dõi từng lượt tải.']
};
$('#page-title').textContent = pageCopy[pageName][0];
$('#page-purpose').textContent = pageCopy[pageName][1];
document.title = pageCopy[pageName][0] + ' · Auralytica';
$(`#workflow-nav a[href="/${pageName}"]`).setAttribute('aria-current','page');
let workflowLoading = false, pageStarted = false;
async function loadWorkflow() {
  if (workflowLoading) return;
  workflowLoading = true;
  $('#workflow-retry').hidden = true;
  try {
    const state = await api('/api/workflow');
    const previous = workflow;
    workflow = state;
    batchActive = state.batch_locked;
    lock(busy);
    $('#workflow-status').textContent = state.active_import
      ? `Nguồn #${state.active_import} · ${state.counts.music.toLocaleString('vi-VN')} nhạc · ${state.counts.rest.toLocaleString('vi-VN')} còn lại${batchActive ? ' · Đang tải: tạm khóa nhập và sửa danh sách.' : ''}`
      : 'Chưa nhập lịch sử.';
    $('#workflow-empty').hidden = pageName === 'import' || !!state.active_import;
    $('#dropzone').hidden = pageName !== 'import';
    $('#explore-summary').hidden = pageName !== 'explore' || !state.active_import;
    $('#metadata-panel').hidden = pageName !== 'explore' || !state.active_import;
    $('.workspace').hidden = pageName !== 'explore' || !state.active_import;
    $('#next-step').hidden = pageName !== 'explore' || !state.active_import;
    $('#dedup-placeholder').hidden = pageName !== 'deduplicate' || !state.active_import;
    $('.download-panel').hidden = pageName !== 'download';
    if (pageName === 'explore' && state.active_import && (!pageStarted || previous?.revision !== state.revision)) {
      if (!pageStarted) restoreExplore();
      pageStarted = true;
      await refresh();
      await loadMetadataPanel();
    }
    if (pageName === 'download' && !pageStarted) { pageStarted = true; await pollDownloads(); }
    if (pageName === 'deduplicate' && state.active_import && !pageStarted) {
      pageStarted = true;
      await loadDedup();
    }
  } catch (error) {
    $('#workflow-status').textContent = error.message;
    $('#workflow-retry').hidden = false;
    // Keep navigation available, but disable mutations until server state is known.
    batchActive = true; lock(busy);
  } finally { workflowLoading = false; }
}
$('#workflow-retry').addEventListener('click',loadWorkflow);
loadWorkflow();
setInterval(() => {
  if (pageName === 'download' && pageStarted) pollDownloads();
  else if ($('#workflow-retry').hidden) loadWorkflow();
},1000);
