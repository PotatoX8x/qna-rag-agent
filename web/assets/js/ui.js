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

// Coloured status chip for document ingestion state.
export function statusPill(status) {
  const span = document.createElement('span');
  span.className = `pill pill-${status}`;
  span.textContent = status;
  return span;
}
