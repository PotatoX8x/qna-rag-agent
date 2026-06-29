import apiFetch from './api.js';

if (localStorage.getItem('token')) {
  location.href = '/app';
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const tabs = document.querySelectorAll('.auth-tab');
const forms = document.querySelectorAll('.auth-form');
const authError = document.getElementById('auth-error');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    forms.forEach(f => f.classList.add('hidden'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.form).classList.remove('hidden');
    clearErrors();
  });
});

function clearErrors() {
  authError.textContent = '';
  document.querySelectorAll('.field-error').forEach(el => (el.textContent = ''));
  document.querySelectorAll('.form-group input').forEach(el => el.classList.remove('invalid'));
}

function setFieldError(id, message) {
  document.getElementById(id).classList.add('invalid');
  document.getElementById(id + '-error').textContent = message;
}

function val(id) {
  return document.getElementById(id).value;
}

function checkEmail(id) {
  const value = val(id).trim();
  if (!value) return setFieldError(id, 'Email is required.'), false;
  if (!EMAIL_RE.test(value)) return setFieldError(id, 'Enter a valid email address.'), false;
  return true;
}

function checkRequired(id, label) {
  if (!val(id)) return setFieldError(id, `${label} is required.`), false;
  return true;
}

// Clear a field's error as soon as the user edits it.
document.querySelectorAll('.form-group input').forEach(input => {
  input.addEventListener('input', () => {
    input.classList.remove('invalid');
    const errorEl = document.getElementById(input.id + '-error');
    if (errorEl) errorEl.textContent = '';
    authError.textContent = '';
  });
});

const loginForm = document.getElementById('login-form');
loginForm.addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  let ok = checkEmail('login-email');
  ok = checkRequired('login-password', 'Password') && ok;
  if (!ok) return;

  const btn = loginForm.querySelector('button[type=submit]');
  btn.disabled = true;
  try {
    const res = await apiFetch('/api/auth/login', {
      method: 'POST',
      redirectOn401: false,
      body: JSON.stringify({
        email: val('login-email').trim(),
        password: val('login-password'),
      }),
    });
    localStorage.setItem('token', res.access_token);
    location.href = '/app';
  } catch (err) {
    authError.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
});

const registerForm = document.getElementById('register-form');
registerForm.addEventListener('submit', async e => {
  e.preventDefault();
  clearErrors();

  let ok = checkEmail('reg-email');

  const password = val('reg-password');
  if (!password) {
    setFieldError('reg-password', 'Password is required.');
    ok = false;
  } else if (new TextEncoder().encode(password).length > 72) {
    setFieldError('reg-password', 'Password must be at most 72 bytes.');
    ok = false;
  }

  if (!val('reg-password-confirm')) {
    setFieldError('reg-password-confirm', 'Please repeat your password.');
    ok = false;
  } else if (password && val('reg-password-confirm') !== password) {
    setFieldError('reg-password-confirm', 'Passwords do not match.');
    ok = false;
  }

  if (!ok) return;

  const btn = registerForm.querySelector('button[type=submit]');
  btn.disabled = true;
  try {
    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      redirectOn401: false,
      body: JSON.stringify({
        email: val('reg-email').trim(),
        password: password,
      }),
    });
    localStorage.setItem('token', res.access_token);
    location.href = '/app';
  } catch (err) {
    authError.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
});
