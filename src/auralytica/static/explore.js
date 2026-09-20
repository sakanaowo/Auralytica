'use strict';
let summaryRevision = 0;
function setRestOpen(open) {
  $('#rest').hidden = !open;
  $('#rest-toggle').setAttribute('aria-expanded',String(open));
  $('#rest-toggle').textContent = open ? 'Thu gọn Còn lại' : 'Mở Còn lại để xem và bổ sung nhạc';
  if (!open && groups.rest) {
    ++groups.rest.revision;
    groups.rest.cancelSearch?.();
    groups.rest.items = []; groups.rest.selected.clear(); groups.rest.loading = false;
    $('tbody',groups.rest.el).replaceChildren();
  }
}
function bars(selector, values) {
  const container = $(selector); container.replaceChildren();
  const max = Math.max(1,...Object.values(values));
  for (const [label,value] of Object.entries(values)) {
    const row = node('div',undefined,'stat-bar');
    const bar = node('progress'); bar.max = max; bar.value = value; bar.setAttribute('aria-label',label);
    row.append(node('span',label),bar,node('span',String(value))); container.append(row);
  }
}
async function loadSummary() {
  const revision = ++summaryRevision;
  $('#summary-status').textContent = 'Đang tính thống kê…';
  $('#summary-retry').hidden = true;
  try {
    const data = await api('/api/explore/summary');
    if (revision !== summaryRevision) return;
    $('#summary-content').hidden = false;
    $('#summary-status').textContent = '';
    $('#import-result').textContent = `Nguồn #${data.import_id}: ${data.import_statistics.unique_videos.toLocaleString('vi-VN')} video · ${data.import_statistics.video_events.toLocaleString('vi-VN')} lượt xem được nhập.`;
    for (const [id,value] of [['videos',data.videos],['watches',data.watch_events],['days',data.watch_days_utc]]) $(`#summary-${id}`).textContent = String(value);
    $('#summary-decisions').textContent = `${data.decisions.user} thủ công · ${data.decisions.automatic} tự nhận dạng · ${data.undated_events} lượt không có ngày hợp lệ.`;
    const m = data.metadata;
    $('#summary-metadata').textContent = `Metadata: ${m.available} có dữ liệu đã lưu · ${m.missing} chưa có · ${m.fresh} cache còn hạn · ${m.stale} cache cũ · ${m.applied} có evidence đã áp dụng. Cache và evidence có thể trùng nhau; cache không tự xác nhận là nhạc.`;
    $('#summary-signals').textContent = `Tiêu đề: ${data.title_signals.music_terms} có từ khóa nhạc · ${data.title_signals.talk_terms} có từ khóa nói chuyện (có thể trùng).`;
    bars('#repeat-chart',data.repeat_distribution); bars('#days-chart',data.day_distribution);
    const channels = $('#channel-stats'); channels.replaceChildren(node('p',`${data.channel_count} nhóm kênh (gồm nhóm chưa biết kênh nếu có).`));
    for (const channel of data.channels) channels.append(node('p',`${channel.name}: ${channel.videos} video · ${channel.watch_events} lượt xem`));
    const dates = $('#recent-days'); dates.replaceChildren();
    for (const day of data.recent_days) dates.append(node('p',`${day.day}: ${day.events} lượt xem`));
    if (!data.recent_days.length) dates.append(node('p','Chưa có ngày xem hợp lệ.'));
  } catch (error) {
    if (revision !== summaryRevision) return;
    $('#summary-content').hidden = true;
    $('#summary-status').textContent = error.message;
    $('#summary-retry').hidden = false;
  }
}
if (pageName === 'explore') {
  $('#rest-toggle').addEventListener('click',() => {
    setRestOpen($('#rest').hidden); saveExplore();
    if (!$('#rest').hidden) load(groups.rest);
  });
  $('#summary-retry').addEventListener('click',loadSummary);
}
