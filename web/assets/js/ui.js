export function el(id) {
  return document.getElementById(id);
}

const VIEWS = ['view-empty', 'view-chat', 'view-kb'];

export function showView(name) {
  VIEWS.forEach(v => el(v).classList.toggle('hidden', v !== name));
}

export function openModal(id) {
  el(id).classList.remove('hidden');
}

export function closeModal(id) {
  el(id).classList.add('hidden');
}

// Tinted status chip for document ingestion state. In-progress states get a
// spinning ring; terminal states get a static dot — both tinted via
// currentColor so they follow each pill's own status color automatically.
export function statusPill(status) {
  const span = document.createElement('span');
  span.className = `pill pill-${status}`;

  const busy = status === 'pending' || status === 'processing';
  const indicator = document.createElement('span');
  indicator.className = busy ? 'pill-spinner' : 'pill-dot';
  span.appendChild(indicator);

  const label = document.createElement('span');
  label.textContent = status;
  span.appendChild(label);

  return span;
}
