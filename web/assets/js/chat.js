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
  const currentKb = activeConv && activeConv.kb_id;
  const list = el('picker-kb-list');
  list.innerHTML = '';
  if (!kbs.length) {
    list.innerHTML = '<div class="list-empty">No knowledge bases yet — create one below.</div>';
  }
  kbs.forEach(kb => {
    const row = document.createElement('div');
    row.className = 'picker-kb-item' + (kb.id === currentKb ? ' active' : '');

    const select = document.createElement('button');
    select.type = 'button';
    select.className = 'picker-kb-select';
    select.textContent = kb.name;
    select.addEventListener('click', () => choosePickerKb(kb));

    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'picker-kb-edit icon-btn';
    edit.title = 'Edit knowledge base';
    setIcon(edit, 'edit');
    edit.addEventListener('click', () => { closeModal('modal-picker'); openBase(kb); });

    row.append(select, edit);
    list.appendChild(row);
  });
  openModal('modal-picker');
}

async function choosePickerKb(kb) {
  closeModal('modal-picker');
  if (pickerMode === 'create') await createConversationWithKb(kb);
  else await bindKb(kb.id);
}

/* Conversations */

async function loadConversations() {
  conversations = await apiFetch('/api/conversations');
  renderConvList();
}

function renderConvList() {
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
  del.addEventListener('click', e => { e.stopPropagation(); confirmDeleteConv(item, conv); });

  actions.append(edit, del);
  item.append(main, actions);
  item.addEventListener('click', () => openConversation(conv.id));
  return item;
}

// Swap the chat row into an inline "Delete chat?" confirm prompt.
function confirmDeleteConv(item, conv) {
  item.innerHTML = '';
  item.classList.add('confirming');

  const text = document.createElement('span');
  text.className = 'row-confirm-text';
  text.textContent = 'Delete chat?';

  const actions = document.createElement('div');
  actions.className = 'row-confirm-actions';

  const no = document.createElement('button');
  no.className = 'row-confirm-no';
  no.type = 'button';
  no.textContent = 'Cancel';
  no.addEventListener('click', e => { e.stopPropagation(); renderConvList(); });

  const yes = document.createElement('button');
  yes.className = 'row-confirm-yes';
  yes.type = 'button';
  yes.textContent = 'Delete';
  yes.addEventListener('click', e => { e.stopPropagation(); deleteConversation(conv.id); });

  actions.append(no, yes);
  item.append(text, actions);
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

  pollDocs(conv.kb_id, applyGate);
}

function applyGate(docs) {
  const ready = docs.some(d => d.status === 'ready');
  const busy = docs.some(d => d.status === 'pending' || d.status === 'processing');
  const textarea = el('chat-input');
  const notice = el('gate-notice');

  textarea.disabled = !ready;
  el('btn-send').disabled = !ready;

  if (ready) {
    notice.classList.add('hidden');
  } else {
    notice.classList.remove('hidden');
    notice.textContent = busy
      ? 'Ingesting your documents… you can chat once at least one document is ready.'
      : 'This knowledge base has no ready documents. Add documents in the Knowledge Bases tab or switch base.';
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
