'use strict';
let dedupRun = null, dedupPage = 1, selectionRevision = 0;

function dedupEvidence(group) {
  if (group.evidence_type === 'confirmed_alias') return 'Alias đã xác nhận';
  return group.artist_conflict ? 'Tên chuẩn hóa giống · kênh/nghệ sĩ khác · cần xem kỹ' : 'Tên chuẩn hóa giống';
}

function memberView(member) {
  const row = node('div',undefined,'dedup-member');
  const keep = node('input'); keep.type = 'checkbox'; keep.checked = member.keep;
  keep.setAttribute('aria-label',`Giữ ${member.raw_title} để tải`);
  keep.addEventListener('change',async () => {
    keep.disabled = true;
    try {
      const result = await api('/api/dedup/selections',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({video_ids:[member.video_id],keep:keep.checked,expected_revision:selectionRevision})});
      selectionRevision = result.revision;
      $('#dedup-status').textContent = `Đã lưu lựa chọn · revision ${selectionRevision}.`;
    } catch (error) {
      $('#dedup-status').textContent = error.message;
      await loadDedupGroups();
    } finally { keep.disabled = false; }
  });
  const thumb = node('div','♪','thumbnail');
  const image = node('img'); image.alt = ''; image.loading = 'lazy'; image.referrerPolicy = 'no-referrer';
  image.src = `https://i.ytimg.com/vi/${member.video_id}/mqdefault.jpg`;
  image.addEventListener('error',() => { image.remove(); thumb.textContent = '♪'; });
  thumb.replaceChildren(image);
  const info = node('div'); const link = node('a',member.raw_title || member.video_id);
  link.href = `https://www.youtube.com/watch?v=${encodeURIComponent(member.video_id)}`;
  link.target = '_blank'; link.rel = 'noopener noreferrer';
  info.append(link,node('p',member.channel || 'Chưa biết kênh'),
    node('div',`${member.version_marker ? 'Phiên bản: '+member.version_marker : 'Không có marker phiên bản'} · Nguồn ghép: ${member.evidence.source}${member.evidence.alias_source ? ' / '+member.evidence.alias_source : ''} · Metadata chi tiết chưa biết`,'dedup-evidence'));
  row.append(keep,thumb,info); return row;
}

function renderDedup(data) {
  dedupRun = data.run; selectionRevision = data.selection_revision;
  const root = $('#dedup-groups'); root.replaceChildren();
  $('#dedup-status').textContent = `${data.total} nhóm gợi ý${data.run.stale ? ' · danh sách đã đổi, hãy quét lại' : ''} · revision ${selectionRevision}.`;
  if (!data.items.length) root.append(node('p','Chưa có nhóm nghi trùng. Bạn vẫn có thể tiếp tục với mọi video được giữ mặc định.'));
  for (const group of data.items) {
    const card = node('section',undefined,'dedup-group'); card.classList.toggle('rejected',group.rejected);
    const head = node('div',undefined,'dedup-group-head');
    const info = node('div'); info.append(node('h3',group.title_key),node('p',`${dedupEvidence(group)} · ${group.member_count} video`));
    const reject = node('button',group.rejected ? 'Hoàn tác không ghép' : 'Không ghép nhóm này','reject-group');
    reject.addEventListener('click',async () => {
      try {
        const result = await api(`/api/dedup/groups/${group.group_id}/rejection`,{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({rejected:!group.rejected,expected_revision:selectionRevision})});
        selectionRevision = result.revision; group.rejected = result.rejected;
        card.classList.toggle('rejected',group.rejected);
        reject.textContent = group.rejected ? 'Hoàn tác không ghép' : 'Không ghép nhóm này';
        $('#dedup-status').textContent = `Đã lưu · revision ${selectionRevision}.`;
      } catch (error) { $('#dedup-status').textContent = error.message; await loadDedupGroups(); }
    });
    head.append(info,reject); card.append(head);
    const members = node('div',undefined,'dedup-members');
    const memberPager = node('div',undefined,'download-actions');
    const memberPrev = node('button','← Bản trước'); const memberLabel = node('span'); const memberNext = node('button','Bản sau →');
    let memberPage = group.member_page;
    function paintMemberPage(items,total,page,pageSize) {
      members.replaceChildren(...items.map(memberView)); memberPage = page;
      const pages = Math.max(1,Math.ceil(total/pageSize)); memberLabel.textContent = `${page} / ${pages}`;
      memberPrev.disabled = page <= 1; memberNext.disabled = page >= pages;
    }
    async function changeMemberPage(page) {
      try {
        const data = await api(`/api/dedup/groups/${group.group_id}/members?page=${page}&page_size=50`);
        selectionRevision = data.selection_revision; paintMemberPage(data.items,data.total,data.page,data.page_size);
      } catch (error) { $('#dedup-status').textContent = error.message; }
    }
    memberPrev.addEventListener('click',() => changeMemberPage(memberPage-1));
    memberNext.addEventListener('click',() => changeMemberPage(memberPage+1));
    paintMemberPage(group.members,group.member_count,group.member_page,group.member_page_size);
    memberPager.append(memberPrev,memberLabel,memberNext);
    const keepAll = node('button','Giữ tất cả bản');
    keepAll.addEventListener('click',async () => {
      try {
        const result = await api(`/api/dedup/groups/${group.group_id}/selection`,{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({keep:true,expected_revision:selectionRevision})});
        selectionRevision = result.revision; await loadDedupGroups();
      } catch (error) { $('#dedup-status').textContent = error.message; }
    });
    card.append(members,memberPager,keepAll); root.append(card);
  }
  const pages = Math.max(1,Math.ceil(data.total/data.page_size));
  $('#dedup-page').textContent = `${dedupPage} / ${pages}`;
  $('#dedup-prev').disabled = dedupPage <= 1; $('#dedup-next').disabled = dedupPage >= pages;
}

async function loadDedupGroups() {
  if (!dedupRun) return;
  try { renderDedup(await api(`/api/dedup/runs/${dedupRun.run_id}/groups?page=${dedupPage}&page_size=20`)); }
  catch (error) { $('#dedup-status').textContent = error.message; }
}

async function loadDedup() {
  try {
    const latest = await api('/api/dedup/runs/latest');
    selectionRevision = latest.selection_revision;
    if (!latest.run) { $('#dedup-status').textContent = 'Chưa quét gợi ý. Mọi video đang được giữ mặc định.'; return; }
    dedupRun = latest.run; await loadDedupGroups();
  } catch (error) { $('#dedup-status').textContent = error.message; }
}

async function startDedup() {
  $('#dedup-status').textContent = 'Đang quét tiêu đề và alias local…';
  $('#dedup-run').disabled = true;
  try { dedupRun = await api('/api/dedup/runs',{method:'POST'}); dedupPage = 1; await loadDedupGroups(); }
  catch (error) { $('#dedup-status').textContent = error.message; }
  finally { $('#dedup-run').disabled = false; }
}

async function confirmManualAlias() {
  const ids = $('#manual-video-ids').value.split(',').map(value => value.trim()).filter(Boolean);
  $('#dedup-status').textContent = 'Đang lưu alias và quét lại…';
  try {
    const result = await api('/api/dedup/aliases',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({video_ids:ids,artist_scope:$('#manual-artist').value.trim() || null})});
    dedupRun = result.run; dedupPage = 1; await loadDedupGroups();
  } catch (error) { $('#dedup-status').textContent = error.message; }
}

if (pageName === 'deduplicate') {
  $('#dedup-run').addEventListener('click',startDedup);
  $('#manual-alias').addEventListener('click',confirmManualAlias);
  $('#dedup-prev').addEventListener('click',() => { --dedupPage; loadDedupGroups(); });
  $('#dedup-next').addEventListener('click',() => { ++dedupPage; loadDedupGroups(); });
}
