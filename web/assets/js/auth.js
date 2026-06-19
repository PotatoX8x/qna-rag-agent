import apiFetch from './api.js';

if (localStorage.getItem('token')) {
  location.href = '/app';
}

const tabs = document.querySelectorAll('.auth-tab');
const forms = document.querySelectorAll('.auth-form');
const errorEl = document.getElementById('auth-error');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    forms.forEach(f => f.classList.add('hidden'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.form).classList.remove('hidden');
    errorEl.textContent = '';
  });
});

function bindForm(formId, path) {
  const form = document.getElementById(formId);
  form.addEventListener('submit', async e => {
    e.preventDefault();
    errorEl.textContent = '';
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;

    const data = Object.fromEntries(new FormData(form));
    try {
      const res = await apiFetch(path, { method: 'POST', body: JSON.stringify(data) });
      localStorage.setItem('token', res.access_token);
      location.href = '/app';
    } catch (err) {
      errorEl.textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
}

bindForm('login-form', '/api/auth/login');
bindForm('register-form', '/api/auth/register');
