import apiFetch from './api.js';

let _selectedKbId = null;

export async function loadKbs(selectEl) {
  const kbs = await apiFetch('/api/knowledge-bases');
  selectEl.innerHTML = '<option value="">Select knowledge base…</option>';
  kbs.forEach(kb => {
    const opt = document.createElement('option');
    opt.value = kb.id;
    opt.textContent = kb.name;
    selectEl.appendChild(opt);
  });
  return kbs;
}

export function getSelectedKbId() {
  return _selectedKbId;
}

export function setSelectedKbId(id) {
  _selectedKbId = id || null;
}
