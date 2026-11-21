/* v89.00: premium behaviour layer - toasts, friendly page-error handling, submit loading states.
   Additive only: it never changes form data or blocks a workflow. */
(function () {
  'use strict';
  function wrap() {
    var w = document.getElementById('mg-toast-wrap');
    if (!w) { w = document.createElement('div'); w.id = 'mg-toast-wrap'; document.body.appendChild(w); }
    return w;
  }
  window.mgToast = function (message, isError) {
    try {
      var t = document.createElement('div');
      t.className = 'mg-toast' + (isError ? ' mg-toast-error' : '');
      t.setAttribute('role', 'status');
      t.textContent = message;
      wrap().appendChild(t);
      setTimeout(function () { t.remove(); }, 6000);
    } catch (e) { /* a toast must never break the page */ }
  };
  /* Friendly handling of unexpected page script errors: tell the user, never show a stack. */
  var shown = false;
  window.addEventListener('error', function () {
    if (shown) return; shown = true;
    window.mgToast('A small page error happened. If something looks wrong, please refresh the page.', true);
  });
  window.addEventListener('unhandledrejection', function () {
    if (shown) return; shown = true;
    window.mgToast('A small page error happened. If something looks wrong, please refresh the page.', true);
  });
  /* Submit buttons show a loading state so a double click is obvious and harmless. */
  document.addEventListener('submit', function (ev) {
    var form = ev.target;
    if (!form || form.dataset.mgNoLoading) return;
    var btn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (btn) { btn.classList.add('mg-loading'); setTimeout(function () { btn.classList.remove('mg-loading'); }, 8000); }
  }, true);
})();
