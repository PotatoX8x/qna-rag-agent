const BASE = '';

// Attaches JWT, handles 401 redirect, throws on non-2xx, returns null on 204.
// Pass redirectOn401:false to throw on 401 instead (e.g. login failures).
async function apiFetch(path, opts = {}) {
  const { redirectOn401 = true, ...fetchOpts } = opts;
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...fetchOpts.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(BASE + path, { ...fetchOpts, headers });

  if (res.status === 401 && redirectOn401) {
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
