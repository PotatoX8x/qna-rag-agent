import apiFetch from './api.js';
import { el, showView, openModal, closeModal, statusPill } from './ui.js';
import { setIcon } from './icons.js';

const BUSY = new Set(['pending', 'processing']);

export function fetchKbs() {
  return apiFetch('/api/knowledge-bases');
}

export function fetchDocs(kbId) {
  return apiFetch(`/api/knowledge-bases/${kbId}/documents`);
}

export function createKb(name) {
  return apiFetch('/api/knowledge-bases', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function renameKb(kbId, name) {
  return apiFetch(`/api/knowledge-bases/${kbId}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  });
}

export function deleteKb(kbId) {
  return apiFetch(`/api/knowledge-bases/${kbId}`, { method: 'DELETE' });
}

export function deleteDoc(kbId, docId) {
  return apiFetch(`/api/knowledge-bases/${kbId}/documents/${docId}`, { method: 'DELETE' });
}

export async function uploadDocs(kbId, files) {
  const uploaded = [];
  for (const file of files) {
    const form = new FormData();
    form.append('file', file);
    uploaded.push(await apiFetch(`/api/knowledge-bases/${kbId}/documents`, {
      method: 'POST',
      body: form,
    }));
  }
  return uploaded;
}

export function hasReadyDoc(docs) {
  return docs.some(d => d.status === 'ready');
}

/* Polling */

let pollTimer = null;

export function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
}

const POLL_INTERVAL_MS = 5000;

// Re-fetch a KB's documents every POLL_INTERVAL_MS until none are still ingesting.
export function pollDocs(kbId, onUpdate) {
  stopPolling();
  const tick = async () => {
    let docs;
    try {
      docs = await fetchDocs(kbId);
    } catch {
      return;
    }
    onUpdate(docs);
    pollTimer = docs.some(d => BUSY.has(d.status)) ? setTimeout(tick, POLL_INTERVAL_MS) : null;
  };
  tick();
}

/* Create-KB modal */

let pendingFiles = [];
let onCreated = null;

export function openCreateKbModal(opts) {
  onCreated = opts.onCreated;
  pendingFiles = [];
  el('create-kb-name').value = '';
  el('create-kb-name-error').textContent = '';
  el('create-kb-error').textContent = '';
  renderPendingFiles();
  openModal('modal-create-kb');
  el('create-kb-name').focus();
}

function renderPendingFiles() {
  const list = el('create-kb-filelist');
  list.innerHTML = '';
  pendingFiles.forEach((file, i) => {
    const row = document.createElement('div');
    row.className = 'file-pending';

    const name = document.createElement('span');
    name.className = 'file-pending-name';
    name.textContent = file.name;

    const remove = document.createElement('button');
    remove.className = 'file-pending-remove';
    remove.type = 'button';
    remove.textContent = '×';
    remove.addEventListener('click', () => {
      pendingFiles.splice(i, 1);
      renderPendingFiles();
    });

    row.append(name, remove);
    list.appendChild(row);
  });
}

function addFiles(fileList) {
  for (const f of fileList) pendingFiles.push(f);
  renderPendingFiles();
}

function wireCreateModal() {
  const drop = el('create-kb-drop');
  const fileInput = el('create-kb-files');

  drop.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    addFiles(fileInput.files);
    fileInput.value = '';
  });

  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
  drop.addEventListener('drop', e => {
    e.preventDefault();
    drop.classList.remove('dragover');
    addFiles(e.dataTransfer.files);
  });

  el('btn-create-kb-cancel').addEventListener('click', () => closeModal('modal-create-kb'));

  el('btn-create-kb-submit').addEventListener('click', async () => {
    const name = el('create-kb-name').value.trim();
    el('create-kb-name-error').textContent = '';
    el('create-kb-error').textContent = '';
    if (!name) {
      el('create-kb-name-error').textContent = 'Name is required.';
      return;
    }

    const submit = el('btn-create-kb-submit');
    submit.disabled = true;
    try {
      const kb = await createKb(name);
      if (pendingFiles.length) await uploadDocs(kb.id, pendingFiles);
      closeModal('modal-create-kb');
      if (onCreated) onCreated(kb);
    } catch (err) {
      el('create-kb-error').textContent = err.message;
    } finally {
      submit.disabled = false;
    }
  });
}

/* Bases sidebar list */

export function renderBasesSidebar(kbs, { selectedId, onSelect }) {
  const list = el('kb-list');
  list.innerHTML = '';
  if (!kbs.length) {
    const empty = document.createElement('div');
    empty.className = 'list-empty';
    empty.textContent = 'No knowledge bases yet.';
    list.appendChild(empty);
    return;
  }
  kbs.forEach(kb => {
    const item = document.createElement('div');
    item.className = 'list-item' + (kb.id === selectedId ? ' active' : '');
    item.title = kb.name;

    const main = document.createElement('div');
    main.className = 'list-item-main';

    const title = document.createElement('span');
    title.className = 'list-item-title';
    title.textContent = kb.name;

    const sub = document.createElement('span');
    sub.className = 'list-item-sub';
    const n = kb.document_count || 0;
    sub.textContent = `${n} document${n === 1 ? '' : 's'}`;

    main.append(title, sub);
    item.appendChild(main);
    item.addEventListener('click', () => onSelect(kb));
    list.appendChild(item);
  });
}

/* KB management view */

export function openKbView(kb, { onChanged }) {
  showView('view-kb');
  el('kb-view-name').textContent = kb.name;
  el('kb-view-desc').textContent = kb.description || '';
  el('kb-doc-list').innerHTML = '<div class="list-empty">Loading…</div>';

  const lingering = el('kb-delete-wrap').querySelector('.confirm-box');
  if (lingering) lingering.remove();

  setIcon(el('btn-kb-rename'), 'edit');
  setIcon(el('btn-kb-refresh'), 'refresh');

  const fileInput = el('kb-file-input');
  const uploadBtn = el('btn-kb-upload');

  uploadBtn.onclick = () => fileInput.click();
  fileInput.onchange = async () => {
    if (!fileInput.files.length) return;
    uploadBtn.disabled = true;
    try {
      await uploadDocs(kb.id, fileInput.files);
    } finally {
      fileInput.value = '';
      uploadBtn.disabled = false;
    }
    pollDocs(kb.id, renderDocs);
    onChanged();
  };

  el('btn-kb-refresh').onclick = () => pollDocs(kb.id, renderDocs);

  el('btn-kb-rename').onclick = () => startKbRename(kb, onChanged);

  el('btn-kb-delete').onclick = () => showKbDeleteConfirm(kb, onChanged);

  function renderDocs(docs) {
    const list = el('kb-doc-list');
    list.innerHTML = '';
    if (!docs.length) {
      list.innerHTML = '<div class="list-empty">No documents. Upload some to get started.</div>';
      return;
    }
    docs.forEach(doc => {
      const row = document.createElement('div');
      row.className = 'doc-row';

      const name = document.createElement('span');
      name.className = 'doc-name';
      name.textContent = doc.filename;
      name.title = doc.error_msg || doc.filename;

      const right = document.createElement('div');
      right.className = 'doc-right';
      right.appendChild(statusPill(doc.status));

      const del = document.createElement('button');
      del.className = 'doc-delete';
      del.type = 'button';
      setIcon(del, 'trash');
      del.title = 'Delete document';
      del.addEventListener('click', async () => {
        await deleteDoc(kb.id, doc.id);
        pollDocs(kb.id, renderDocs);
        onChanged();
      });
      right.appendChild(del);

      row.append(name, right);
      list.appendChild(row);
    });
  }

  pollDocs(kb.id, renderDocs);
}

function showKbDeleteConfirm(kb, onChanged) {
  const wrap = el('kb-delete-wrap');
  if (wrap.querySelector('.confirm-box')) return;

  const box = document.createElement('div');
  box.className = 'confirm-box';

  const msg = document.createElement('p');
  msg.className = 'confirm-text';
  msg.textContent = 'Are you sure you want to delete this knowledge base?';

  const actions = document.createElement('div');
  actions.className = 'confirm-actions';

  const no = document.createElement('button');
  no.className = 'btn-secondary';
  no.type = 'button';
  no.textContent = 'Cancel';
  no.addEventListener('click', () => box.remove());

  const yes = document.createElement('button');
  yes.className = 'btn-danger';
  yes.type = 'button';
  yes.textContent = 'Delete';
  yes.addEventListener('click', async () => {
    await deleteKb(kb.id);
    stopPolling();
    onChanged({ deleted: kb.id });
  });

  actions.append(no, yes);
  box.append(msg, actions);
  wrap.appendChild(box);
}

function startKbRename(kb, onChanged) {
  const nameEl = el('kb-view-name');
  const input = document.createElement('input');
  input.className = 'kb-name-input';
  input.value = kb.name;
  nameEl.replaceWith(input);
  input.focus();
  input.select();

  let done = false;
  const finish = async commit => {
    if (done) return;
    done = true;
    const name = input.value.trim();
    let label = kb.name;
    if (commit && name && name !== kb.name) {
      const updated = await renameKb(kb.id, name);
      kb.name = updated.name;
      label = updated.name;
      onChanged();
    }
    const h2 = document.createElement('h2');
    h2.id = 'kb-view-name';
    h2.className = 'kb-view-name';
    h2.textContent = label;
    input.replaceWith(h2);
  };

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); finish(true); }
    else if (e.key === 'Escape') finish(false);
  });
  input.addEventListener('blur', () => finish(true));
}

wireCreateModal();
