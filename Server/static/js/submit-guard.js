/* Stage 8: double-submit guard. When a form is submitted, its submit buttons
   are disabled until the next page loads, so a double click cannot post a
   sale, purchase or payment twice. Forms with data-no-guard are left alone,
   and buttons are restored if the browser comes back from the back-cache. */
(function () {
    document.addEventListener('submit', function (ev) {
        var form = ev.target;
        if (!form || form.tagName !== 'FORM' || form.hasAttribute('data-no-guard')) return;
        if ((form.getAttribute('method') || 'get').toLowerCase() === 'get') return;
        var btns = form.querySelectorAll('button[type="submit"], input[type="submit"]');
        setTimeout(function () {
            btns.forEach(function (b) { b.disabled = true; b.classList.add('mg-busy'); });
        }, 0);
    }, true);
    window.addEventListener('pageshow', function () {
        document.querySelectorAll('button.mg-busy, input.mg-busy').forEach(function (b) {
            b.disabled = false; b.classList.remove('mg-busy');
        });
    });
})();
