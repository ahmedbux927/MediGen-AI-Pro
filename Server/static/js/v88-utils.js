/* v88.00: E5 - debounced search helper. Usage: mgDebounce(fn, 250) */
window.mgDebounce = function (fn, wait) {
  var t = null;
  return function () {
    var args = arguments, self = this;
    clearTimeout(t);
    t = setTimeout(function () { fn.apply(self, args); }, wait || 250);
  };
};
/* Attach to any input with [data-mg-search-for="<form id>"]: typing submits after 250ms idle, no full re-render per keystroke. */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('input[data-mg-search-for]').forEach(function (inp) {
    var form = document.getElementById(inp.getAttribute('data-mg-search-for'));
    if (!form) return;
    inp.addEventListener('input', window.mgDebounce(function () { form.requestSubmit ? form.requestSubmit() : form.submit(); }, 250));
  });
});
