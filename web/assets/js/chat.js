import apiFetch from './api.js';
import { el, showView, openModal, closeModal } from './ui.js';
import { setIcon } from './icons.js';
import {
  fetchKbs,
  openCreateKbModal,
  renderBasesSidebar,
  openKbView,
  pollDocs,
  stopPolling,
} from './kb.js';

let conversations = [];
let activeConv = null;
let kbs = [];
let kbsById = {};
let selectedBaseId = null;
let pickerMode = 'create';
let pickerSelectedKb = null;
let pickerSearchTerm = '';

// Cache of fetched conversation details (id -> detail with messages). Kept in
// sync locally on send/rename; invalidated on send failure and delete.
const convCache = {};

const userLabel = el('user-label');

// Display-only decode — signature verification happens server-side.
function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return {};
  }
}

async function init() {
  const token = localStorage.getItem('token');
  if (!token) { location.href = '/'; return; }
  userLabel.textContent = parseJwt(token).email || 'User';

  document.querySelectorAll('.rail-btn').forEach(b => setIcon(b, b.dataset.icon));
  setIcon(el('btn-send'), 'send');
  setIcon(document.querySelector('.picker-search-icon'), 'search');

  wireSidebar();
  wirePicker();
  wireChat();
  wireSourcePanel();

  await refreshKbs();
  await loadConversations();
  restoreLastView();
}

function saveLastView(type, id) {
  localStorage.setItem('lastView', JSON.stringify({ type, id }));
}

function clearLastView() {
  localStorage.removeItem('lastView');
}

// Re-open the chat or knowledge base that was active before a page refresh.
function restoreLastView() {
  let v = null;
  try {
    v = JSON.parse(localStorage.getItem('lastView') || 'null');
  } catch {
    v = null;
  }
  if (!v) return;
  if (v.type === 'chat' && conversations.some(c => c.id === v.id)) {
    openConversation(v.id);
  } else if (v.type === 'base' && kbsById[v.id]) {
    openBase(kbsById[v.id]);
  }
}

function wireSidebar() {
  document.querySelectorAll('.rail-btn').forEach(btn => {
    btn.addEventListener('click', () => selectTab(btn.dataset.tab));
  });

  el('btn-new-chat').addEventListener('click', newConversation);
  el('btn-new-base').addEventListener('click', () => {
    openCreateKbModal({ onCreated: async kb => { await refreshKbs(); openBase(kb); } });
  });

  el('btn-logout').addEventListener('click', () => {
    localStorage.removeItem('token');
    location.href = '/';
  });

  el('kb-chip').addEventListener('click', () => openPicker('switch'));

  el('conv-list').addEventListener('scroll', closeRowConfirm);
  document.addEventListener('click', e => {
    if (rowConfirmBox && !rowConfirmBox.contains(e.target)) closeRowConfirm();
  });
}

function selectTab(name) {
  document.querySelectorAll('.rail-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === name);
  });
  el('tab-chats').classList.toggle('hidden', name !== 'chats');
  el('tab-bases').classList.toggle('hidden', name !== 'bases');
  el('sidebar-section').textContent = name === 'bases' ? 'Knowledge Bases' : 'Chats';
}

/* Knowledge bases */

async function refreshKbs() {
  kbs = await fetchKbs();
  kbsById = Object.fromEntries(kbs.map(kb => [kb.id, kb]));
  renderBasesSidebar(kbs, { selectedId: selectedBaseId, onSelect: openBase });
}

function openBase(kb) {
  selectedBaseId = kb.id;
  selectTab('bases');
  el('kb-chip').classList.add('hidden');
  stopPolling();
  closeSourcePanel();
  saveLastView('base', kb.id);
  renderBasesSidebar(kbs, { selectedId: selectedBaseId, onSelect: openBase });
  openKbView(kb, { onChanged: onBaseChanged });
}

async function onBaseChanged(info = {}) {
  if (info && info.deleted) {
    const deletedId = info.deleted;
    selectedBaseId = null;
    // The backend nulls kb_id on any chat that used this base (ON DELETE SET NULL);
    // mirror that in the local list and cache so subtitles/pickers stay correct.
    conversations.forEach(c => { if (c.kb_id === deletedId) c.kb_id = null; });
    Object.values(convCache).forEach(d => { if (d.kb_id === deletedId) d.kb_id = null; });
    if (activeConv && activeConv.kb_id === deletedId) activeConv.kb_id = null;
    clearLastView();
    showView('view-empty');
  }
  await refreshKbs();
  renderConvList();
}

/* KB picker modal */

function wirePicker() {
  el('btn-picker-cancel').addEventListener('click', () => {
    closeModal('modal-picker');
    if (!activeConv) showView('view-empty');
  });

  el('picker-search').addEventListener('input', e => {
    pickerSearchTerm = e.target.value.trim().toLowerCase();
    renderPickerList();
  });

  el('btn-picker-confirm').addEventListener('click', async () => {
    if (!pickerSelectedKb) return;
    closeModal('modal-picker');
    if (pickerMode === 'create') await createConversationWithKb(pickerSelectedKb);
    else await bindKb(pickerSelectedKb.id);
  });

  el('btn-picker-new').addEventListener('click', () => {
    closeModal('modal-picker');
    openCreateKbModal({
      onCreated: async kb => {
        await refreshKbs();
        if (pickerMode === 'create') await createConversationWithKb(kb);
        else await bindKb(kb.id);
      },
    });
  });
}

function openPicker(mode) {
  pickerMode = mode;
  pickerSearchTerm = '';
  el('picker-search').value = '';
  const currentKbId = activeConv && activeConv.kb_id;
  pickerSelectedKb = (currentKbId && kbsById[currentKbId]) || null;
  el('btn-picker-confirm').textContent = mode === 'create' ? 'Create chat' : 'Switch knowledge base';
  el('btn-picker-confirm').disabled = !pickerSelectedKb;
  renderPickerList();
  openModal('modal-picker');
}

// Rebuilds the picker list from `kbs`, filtered by `pickerSearchTerm`.
function renderPickerList() {
  const list = el('picker-kb-list');
  list.innerHTML = '';

  const filtered = pickerSearchTerm
    ? kbs.filter(kb => kb.name.toLowerCase().includes(pickerSearchTerm))
    : kbs;

  if (!kbs.length) {
    const empty = document.createElement('div');
    empty.className = 'list-empty';
    empty.textContent = 'No knowledge bases yet — create one below.';
    list.appendChild(empty);
  } else if (!filtered.length) {
    const empty = document.createElement('div');
    empty.className = 'list-empty';
    empty.textContent = 'No matches.';
    list.appendChild(empty);
  }

  filtered.forEach(kb => {
    const active = pickerSelectedKb && kb.id === pickerSelectedKb.id;

    // Editing a KB mid-pick only makes sense when reassigning an already
    // existing chat — a brand-new draft chat has nothing to lose focus from.
    if (pickerMode !== 'switch') {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'picker-kb-item picker-kb-item-solo' + (active ? ' active' : '');
      row.textContent = kb.name;
      row.addEventListener('click', () => selectPickerKb(kb));
      list.appendChild(row);
      return;
    }

    const row = document.createElement('div');
    row.className = 'picker-kb-item picker-kb-item-row' + (active ? ' active' : '');

    const select = document.createElement('button');
    select.type = 'button';
    select.className = 'picker-kb-select';
    select.textContent = kb.name;
    select.addEventListener('click', () => selectPickerKb(kb));

    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'picker-kb-edit icon-btn';
    edit.title = 'Edit knowledge base';
    setIcon(edit, 'edit');
    edit.addEventListener('click', () => { closeModal('modal-picker'); openBase(kb); });

    row.append(select, edit);
    list.appendChild(row);
  });
}

function selectPickerKb(kb) {
  pickerSelectedKb = kb;
  el('btn-picker-confirm').disabled = false;
  renderPickerList();
}

/* Conversations */

async function loadConversations() {
  conversations = await apiFetch('/api/conversations');
  renderConvList();
}

function renderConvList() {
  closeRowConfirm();
  const list = el('conv-list');
  list.innerHTML = '';
  if (!conversations.length) {
    list.innerHTML = '<div class="list-empty">No chats yet.</div>';
    return;
  }
  conversations.forEach(conv => list.appendChild(makeConvItem(conv)));
}

function makeConvItem(conv) {
  const item = document.createElement('div');
  item.className = 'list-item' + (activeConv && conv.id === activeConv.id ? ' active' : '');
  item.dataset.id = conv.id;

  const main = document.createElement('div');
  main.className = 'list-item-main';

  const title = document.createElement('span');
  title.className = 'list-item-title';
  title.textContent = conv.title || 'New chat';

  const sub = document.createElement('span');
  sub.className = 'list-item-sub';
  const kb = kbsById[conv.kb_id];
  sub.textContent = kb ? kb.name : 'No knowledge base';

  main.append(title, sub);

  const actions = document.createElement('div');
  actions.className = 'list-item-actions';

  const edit = document.createElement('button');
  edit.className = 'list-item-edit';
  edit.type = 'button';
  setIcon(edit, 'edit');
  edit.title = 'Rename chat';
  edit.addEventListener('click', e => { e.stopPropagation(); startRename(item, conv); });

  const del = document.createElement('button');
  del.className = 'list-item-delete';
  del.type = 'button';
  setIcon(del, 'trash');
  del.title = 'Delete chat';
  del.addEventListener('click', e => { e.stopPropagation(); confirmDeleteConv(del, conv); });

  actions.append(edit, del);
  item.append(main, actions);
  item.addEventListener('click', () => openConversation(conv.id));
  return item;
}

// Popover "Delete chat?" prompt, fixed-positioned and centered under the
// delete button. Lives on <body> so it stays visible even once the cursor
// leaves the row (the row's action icons fade out on mouse-leave).
let rowConfirmBox = null;

function confirmDeleteConv(anchor, conv) {
  closeRowConfirm();

  const box = document.createElement('div');
  box.className = 'row-confirm-box';

  const text = document.createElement('p');
  text.className = 'row-confirm-text';
  text.textContent = 'Delete this chat?';

  const actions = document.createElement('div');
  actions.className = 'row-confirm-actions';

  const no = document.createElement('button');
  no.className = 'row-confirm-no';
  no.type = 'button';
  no.textContent = 'Cancel';
  no.addEventListener('click', e => { e.stopPropagation(); closeRowConfirm(); });

  const yes = document.createElement('button');
  yes.className = 'row-confirm-yes';
  yes.type = 'button';
  yes.textContent = 'Delete';
  yes.addEventListener('click', e => { e.stopPropagation(); deleteConversation(conv.id); });

  actions.append(no, yes);
  box.append(text, actions);
  box.addEventListener('click', e => e.stopPropagation());
  document.body.appendChild(box);

  const r = anchor.getBoundingClientRect();
  const b = box.getBoundingClientRect();
  const margin = 8;
  const left = Math.max(margin, Math.min(r.left + r.width / 2 - b.width / 2, window.innerWidth - b.width - margin));
  box.style.left = `${left}px`;
  box.style.top = `${r.bottom + 6}px`;

  rowConfirmBox = box;
}

function closeRowConfirm() {
  if (rowConfirmBox) {
    rowConfirmBox.remove();
    rowConfirmBox = null;
  }
}

function startRename(item, conv) {
  const title = item.querySelector('.list-item-title');
  const input = document.createElement('input');
  input.className = 'list-item-rename';
  input.value = conv.title || '';
  title.replaceWith(input);
  input.focus();
  input.select();

  let done = false;
  const finish = async commit => {
    if (done) return;
    done = true;
    const name = input.value.trim();
    if (commit && name && name !== conv.title) {
      const updated = await apiFetch(`/api/conversations/${conv.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: name }),
      });
      conv.title = updated.title;
      if (convCache[conv.id]) convCache[conv.id].title = updated.title;
      if (activeConv && activeConv.id === conv.id) activeConv.title = updated.title;
    }
    renderConvList();
  };

  input.addEventListener('click', e => e.stopPropagation());
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); finish(true); }
    else if (e.key === 'Escape') finish(false);
  });
  input.addEventListener('blur', () => finish(true));
}

function newConversation() {
  activeConv = null;
  selectTab('chats');
  closeSourcePanel();
  clearLastView();
  renderConvList();
  el('kb-chip').classList.add('hidden');
  showView('view-empty');
  openPicker('create');
}

async function createConversationWithKb(kb) {
  const conv = await apiFetch('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({ kb_id: kb.id }),
  });
  conversations.unshift(conv);
  selectTab('chats');
  await openConversation(conv.id);
}

async function openConversation(id) {
  stopPolling();
  closeSourcePanel();
  let detail = convCache[id];
  if (!detail) {
    detail = await apiFetch(`/api/conversations/${id}`);
    convCache[id] = detail;
  }
  activeConv = detail;
  selectedBaseId = null;
  saveLastView('chat', id);
  renderConvList();

  if (detail.kb_id) {
    openChatView(detail);
  } else {
    showView('view-empty');
    openPicker('switch');
  }
}

async function deleteConversation(id) {
  await apiFetch(`/api/conversations/${id}`, { method: 'DELETE' });
  delete convCache[id];
  conversations = conversations.filter(c => c.id !== id);
  if (activeConv && activeConv.id === id) {
    activeConv = null;
    stopPolling();
    el('kb-chip').classList.add('hidden');
    clearLastView();
    showView('view-empty');
  }
  renderConvList();
}

async function bindKb(kbId) {
  const updated = await apiFetch(`/api/conversations/${activeConv.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ kb_id: kbId }),
  });
  activeConv.kb_id = updated.kb_id;
  const listed = conversations.find(c => c.id === activeConv.id);
  if (listed) listed.kb_id = updated.kb_id;
  renderConvList();
  openChatView(activeConv);
}

/* Chat view */

function openChatView(conv) {
  showView('view-chat');
  const kb = kbsById[conv.kb_id];
  const chip = el('kb-chip');
  chip.innerHTML = '';
  const icon = document.createElement('span');
  icon.className = 'kb-chip-icon';
  setIcon(icon, 'bases');
  const label = document.createElement('span');
  label.textContent = kb ? kb.name : 'Select base';
  chip.append(icon, label);
  chip.classList.remove('hidden');

  const thread = el('thread');
  thread.innerHTML = '';
  (conv.messages || []).forEach(m => appendMessage(m.role, m.content, m.citations || []));
  thread.scrollTop = thread.scrollHeight;

  pollDocs(conv.kb_id, docs => applyGate(docs, conv.kb_id));
}

function applyGate(docs, kbId) {
  const ready = docs.some(d => d.status === 'ready');
  const busy = docs.some(d => d.status === 'pending' || d.status === 'processing');
  const textarea = el('chat-input');
  const notice = el('gate-notice');

  textarea.disabled = !ready;
  el('btn-send').disabled = !ready;

  if (ready) {
    notice.classList.add('hidden');
    notice.innerHTML = '';
    return;
  }

  notice.classList.remove('hidden');
  notice.innerHTML = '';

  const text = document.createElement('span');
  text.textContent = busy
    ? 'Ingesting your documents… you can chat once at least one document is ready.'
    : 'This knowledge base has no ready documents.';
  notice.appendChild(text);

  const kb = kbsById[kbId];
  if (kb) {
    const link = document.createElement('button');
    link.type = 'button';
    link.className = 'gate-notice-link';
    link.textContent = 'Manage documents';
    link.addEventListener('click', () => openBase(kb));
    notice.appendChild(link);
  }
}

function wireChat() {
  el('btn-send').addEventListener('click', sendMessage);
  el('thread').addEventListener('scroll', hideCiteTip);

  const textarea = el('chat-input');
  textarea.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
  });
}

function appendMessage(role, content, citations = []) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (role === 'assistant') {
    bubble.appendChild(renderAnswer(content, citations));
  } else {
    bubble.textContent = content;
  }
  wrap.appendChild(bubble);

  const thread = el('thread');
  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
  return wrap;
}

// Turn inline [n] markers in an answer into citations numbered from 1 that
// reveal the source passage on hover. Indices map to the model's 0-based ids.
function renderAnswer(content, citations) {
  const byIndex = {};
  citations.forEach(c => { if (c.index != null) byIndex[c.index] = c; });

  const frag = document.createDocumentFragment();
  const re = /\[(\d+)\]/g;
  let last = 0;
  let m;
  while ((m = re.exec(content)) !== null) {
    if (m.index > last) frag.appendChild(document.createTextNode(content.slice(last, m.index)));
    const n = parseInt(m[1], 10);
    frag.appendChild(makeCite(n, byIndex[n]));
    last = re.lastIndex;
  }
  if (last < content.length) frag.appendChild(document.createTextNode(content.slice(last)));
  return frag;
}

function makeCite(n, citation) {
  const sup = document.createElement('sup');
  sup.className = 'cite';
  sup.textContent = `[${n + 1}]`;
  if (citation && citation.snippet) {
    const quote = formatQuote(citation.snippet);
    sup.addEventListener('mouseenter', () => showCiteTip(sup, quote));
    sup.addEventListener('mouseleave', hideCiteTip);
    sup.addEventListener('click', () => { hideCiteTip(); openSourcePanel(n, citation); });
  } else {
    sup.classList.add('cite-plain');
  }
  return sup;
}

function openSourcePanel(n, citation) {
  el('source-panel-title').textContent = `Source [${n + 1}]`;
  const body = el('source-panel-body');
  body.innerHTML = '';

  const text = document.createElement('div');
  text.className = 'source-text';
  text.textContent = citation.snippet ? citation.snippet.trim() : 'No source text available.';
  body.appendChild(text);

  el('source-panel').classList.remove('hidden');
  el('view-chat').classList.add('panel-open');
}

function closeSourcePanel() {
  el('source-panel').classList.add('hidden');
  el('view-chat').classList.remove('panel-open');
}

function wireSourcePanel() {
  el('source-close').addEventListener('click', closeSourcePanel);

  const resizer = el('source-resizer');
  const panel = el('source-panel');
  let startX = 0;
  let startW = 0;
  let pendingW = 0;
  let frame = 0;
  let overlay = null;

  const apply = () => {
    frame = 0;
    panel.style.width = `${pendingW}px`;
  };
  const onMove = e => {
    pendingW = Math.round(Math.max(240, Math.min(startW + (startX - e.clientX), window.innerWidth * 0.6)));
    if (!frame) frame = requestAnimationFrame(apply);
  };
  const onUp = () => {
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.classList.remove('resizing');
    if (frame) { cancelAnimationFrame(frame); frame = 0; }
    if (overlay) { overlay.remove(); overlay = null; }
  };
  resizer.addEventListener('mousedown', e => {
    e.preventDefault();
    startX = e.clientX;
    startW = panel.getBoundingClientRect().width;
    overlay = document.createElement('div');
    overlay.className = 'resize-overlay';
    document.body.appendChild(overlay);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    document.body.classList.add('resizing');
  });
}

// Collapse whitespace, cap length, and frame as an excerpt with ellipses.
function formatQuote(snippet) {
  const max = 180;
  let s = snippet.trim().replace(/\s+/g, ' ');
  if (s.length > max) s = s.slice(0, max).trimEnd();
  return `…${s}…`;
}

let citeTip = null;

function showCiteTip(target, quote) {
  if (!citeTip) {
    citeTip = document.createElement('div');
    citeTip.className = 'cite-tip';
    document.body.appendChild(citeTip);
  }
  citeTip.textContent = quote;
  citeTip.style.display = 'block';

  const r = target.getBoundingClientRect();
  const tip = citeTip.getBoundingClientRect();
  const margin = 8;

  let left = r.left + r.width / 2 - tip.width / 2;
  left = Math.max(margin, Math.min(left, window.innerWidth - tip.width - margin));

  let top = r.top - tip.height - 6;
  if (top < margin) top = r.bottom + 6;

  citeTip.style.left = `${left}px`;
  citeTip.style.top = `${top}px`;
}

function hideCiteTip() {
  if (citeTip) citeTip.style.display = 'none';
}

// Animated three-dot placeholder while the agent is running.
function appendThinking() {
  const wrap = document.createElement('div');
  wrap.className = 'message assistant';
  const bubble = document.createElement('div');
  bubble.className = 'bubble thinking';
  bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  wrap.appendChild(bubble);
  const thread = el('thread');
  thread.appendChild(wrap);
  thread.scrollTop = thread.scrollHeight;
  return wrap;
}

async function sendMessage() {
  const textarea = el('chat-input');
  const text = textarea.value.trim();
  if (!text || !activeConv) return;

  const conv = activeConv;
  const firstTurn = !(conv.messages && conv.messages.length);

  textarea.value = '';
  textarea.style.height = 'auto';
  el('btn-send').disabled = true;
  textarea.disabled = true;

  appendMessage('user', text);
  const thinking = appendThinking();

  try {
    const res = await apiFetch(`/api/conversations/${conv.id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message: text }),
    });
    thinking.remove();
    appendMessage('assistant', res.answer, res.citations || []);
    conv.messages = conv.messages || [];
    conv.messages.push({ role: 'user', content: text });
    conv.messages.push({ role: 'assistant', content: res.answer, citations: res.citations || [] });
    if (firstTurn && !conv.title) generateTitle(conv.id);
  } catch (err) {
    thinking.remove();
    appendMessage('assistant', `Error: ${err.message}`);
    delete convCache[conv.id];
  } finally {
    el('btn-send').disabled = false;
    textarea.disabled = false;
    textarea.focus();
  }
}

// Ask the backend to title an untitled chat after its first exchange.
// Fire-and-forget: never blocks the chat flow; fills the sidebar when ready.
async function generateTitle(convId) {
  try {
    const res = await apiFetch(`/api/conversations/${convId}/title`, { method: 'POST' });
    if (!res || !res.title) return;
    if (activeConv && activeConv.id === convId) activeConv.title = res.title;
    if (convCache[convId]) convCache[convId].title = res.title;
    const listed = conversations.find(c => c.id === convId);
    if (listed) listed.title = res.title;
    renderConvList();
  } catch {
    /* titling is non-critical */
  }
}

init();
