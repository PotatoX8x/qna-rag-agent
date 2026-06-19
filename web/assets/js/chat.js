import apiFetch from './api.js';
import { loadKbs, getSelectedKbId, setSelectedKbId } from './kb.js';

let activeConvId = null;

const kbSelect   = document.getElementById('kb-select');
const btnNewConv = document.getElementById('btn-new-conv');
const convList   = document.getElementById('conv-list');
const mainHeader = document.getElementById('main-header');
const emptyState = document.getElementById('empty-state');
const threadEl   = document.getElementById('thread');
const inputBar   = document.getElementById('input-bar');
const textarea   = document.getElementById('chat-input');
const btnSend    = document.getElementById('btn-send');
const userLabel  = document.getElementById('user-label');
const btnLogout  = document.getElementById('btn-logout');

// Display-only decode — signature verification happens server-side.
function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch {
    return {};
  }
}

function showThread() {
  emptyState.style.display = 'none';
  threadEl.style.display   = 'flex';
  inputBar.style.display   = 'flex';
}

function showEmpty() {
  emptyState.style.display = 'flex';
  threadEl.style.display   = 'none';
  inputBar.style.display   = 'none';
}

function init() {
  const token = localStorage.getItem('token');
  if (!token) { location.href = '/'; return; }

  userLabel.textContent = parseJwt(token).email || 'User';

  loadKbs(kbSelect).then(loadConversations);

  kbSelect.addEventListener('change', () => {
    setSelectedKbId(kbSelect.value);
    btnNewConv.disabled = !kbSelect.value;
  });

  btnNewConv.addEventListener('click', newConversation);
  btnSend.addEventListener('click', sendMessage);

  btnLogout.addEventListener('click', () => {
    localStorage.removeItem('token');
    location.href = '/';
  });

  textarea.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
  });
}

/* Conversation list */

async function loadConversations() {
  const convs = await apiFetch('/api/conversations');
  convList.innerHTML = '';
  convs.forEach(conv => convList.appendChild(makeConvItem(conv)));
}

function makeConvItem(conv) {
  const el = document.createElement('div');
  el.className = 'conv-item' + (conv.id === activeConvId ? ' active' : '');
  el.dataset.id = conv.id;

  const title = document.createElement('span');
  title.className = 'conv-title';
  title.textContent = conv.title || 'Untitled';

  const del = document.createElement('button');
  del.className = 'conv-delete';
  del.textContent = '×';
  del.title = 'Delete conversation';
  del.addEventListener('click', e => { e.stopPropagation(); deleteConversation(conv.id); });

  el.appendChild(title);
  el.appendChild(del);
  el.addEventListener('click', () => openConversation(conv.id));
  return el;
}

async function newConversation() {
  const kbId = getSelectedKbId();
  if (!kbId) return;
  const conv = await apiFetch('/api/conversations', {
    method: 'POST',
    body: JSON.stringify({ kb_id: kbId }),
  });
  await loadConversations();
  openConversation(conv.id);
}

async function openConversation(id) {
  activeConvId = id;
  document.querySelectorAll('.conv-item').forEach(el => {
    el.classList.toggle('active', el.dataset.id === id);
  });

  const detail = await apiFetch(`/api/conversations/${id}`);
  mainHeader.textContent = detail.title || 'Untitled';
  showThread();
  threadEl.innerHTML = '';
  detail.messages.forEach(m => appendMessage(m.role, m.content, []));
  threadEl.scrollTop = threadEl.scrollHeight;
}

async function deleteConversation(id) {
  await apiFetch(`/api/conversations/${id}`, { method: 'DELETE' });
  if (activeConvId === id) {
    activeConvId = null;
    mainHeader.textContent = '';
    threadEl.innerHTML = '';
    showEmpty();
  }
  await loadConversations();
}

/* Thread rendering */

function appendMessage(role, content, citations = []) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = content;
  wrap.appendChild(bubble);

  if (citations.length) {
    const chips = document.createElement('div');
    chips.className = 'citations';
    citations.forEach((c, i) => {
      const chip = document.createElement('span');
      chip.className = 'citation-chip';
      chip.textContent = `[${i + 1}] score ${c.score.toFixed(2)}`;
      chips.appendChild(chip);
    });
    wrap.appendChild(chips);
  }

  threadEl.appendChild(wrap);
  threadEl.scrollTop = threadEl.scrollHeight;
  return wrap;
}

// Animated three-dot placeholder while the agent is running.
function appendThinking() {
  const wrap = document.createElement('div');
  wrap.className = 'message assistant';
  const bubble = document.createElement('div');
  bubble.className = 'bubble thinking';
  bubble.innerHTML =
    '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  wrap.appendChild(bubble);
  threadEl.appendChild(wrap);
  threadEl.scrollTop = threadEl.scrollHeight;
  return wrap;
}

/* Send */

async function sendMessage() {
  const text = textarea.value.trim();
  if (!text || !activeConvId) return;

  textarea.value = '';
  textarea.style.height = 'auto';
  btnSend.disabled  = true;
  textarea.disabled = true;

  appendMessage('user', text);
  const thinking = appendThinking();

  try {
    const res = await apiFetch(`/api/conversations/${activeConvId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message: text }),
    });
    thinking.remove();
    appendMessage('assistant', res.answer, res.citations || []);
  } catch (err) {
    thinking.remove();
    appendMessage('assistant', `Error: ${err.message}`);
  } finally {
    btnSend.disabled  = false;
    textarea.disabled = false;
    textarea.focus();
  }
}

init();
