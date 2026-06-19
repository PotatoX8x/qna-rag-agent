const BASE = '';

// Attaches JWT, handles 401 redirect, throws on non-2xx, returns null on 204.
async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...opts.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(BASE + path, { ...opts, headers });

  if (res.status === 401) {
    localStorage.removeItem('token');
    location.href = '/';
    return;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  if (res.status === 204) return null;
  return res.json();
}

export default apiFetch;
