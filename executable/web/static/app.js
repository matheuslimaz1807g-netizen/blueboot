/**
 * app.js — Shared client-side utilities for the ApenasPromo local web interface.
 * Per-page logic lives in inline <script> blocks in each template.
 */

// Utility: debounce a function
function debounce(fn, delay) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// Utility: format a UTC timestamp to local date-time string
function fmtDatetime(isoStr) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleString('pt-BR');
}

// Show/hide password toggle (used globally via onclick)
function togglePass(inputId) {
  const el = document.getElementById(inputId);
  if (!el) return;
  el.type = el.type === 'password' ? 'text' : 'password';
}

// Simple toast notification (id="toast" must exist in page)
function showToast(msg, type = 'success') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = [
    'fixed bottom-6 right-6 z-50 px-5 py-3 rounded-xl font-medium text-sm shadow-xl',
    type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white',
  ].join(' ');
  el.classList.remove('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), 3000);
}
