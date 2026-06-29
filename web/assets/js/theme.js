// Classic script loaded in <head> so the stored theme applies before first paint.
(function () {
  const KEY = 'theme';
  const root = document.documentElement;

  function preferred() {
    const stored = localStorage.getItem(KEY);
    if (stored) return stored;
    const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return dark ? 'dark' : 'light';
  }

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    localStorage.setItem(KEY, theme);
    refreshIcons();
  }

  function refreshIcons() {
    const dark = root.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('.theme-toggle').forEach(btn => {
      btn.textContent = dark ? '☀' : '☾';
      btn.title = dark ? 'Switch to light theme' : 'Switch to dark theme';
    });
  }

  // Apply immediately to avoid a flash of the wrong theme.
  root.setAttribute('data-theme', preferred());

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.theme-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        apply(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
      });
    });
    refreshIcons();
  });
})();
