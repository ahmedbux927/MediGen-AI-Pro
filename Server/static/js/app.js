/* MediGen shared helpers (Step 8). Loaded on every page from base.html.
   No external libraries, works offline. */
(function (window) {
    'use strict';

    var MediGen = window.MediGen || {};

    /* Security token that the server puts in the page (meta tag). Every POST needs it. */
    MediGen.csrfToken = function () {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    };

    /* Send a POST with the token in the header. Returns a fetch promise. */
    MediGen.post = function (url, body) {
        var headers = { 'X-CSRFToken': MediGen.csrfToken() };
        var opts = { method: 'POST', headers: headers, credentials: 'same-origin' };
        if (body instanceof FormData) {
            opts.body = body;
        } else if (body) {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        return fetch(url, opts);
    };

    /* Small message in the top-right corner. type: 'success' | 'danger' | 'warning' | 'info'. */
    MediGen.toast = function (message, type) {
        var box = document.getElementById('mediToastBox');
        if (!box) {
            box = document.createElement('div');
            box.id = 'mediToastBox';
            box.setAttribute('role', 'status');
            box.setAttribute('aria-live', 'polite');
            box.style.cssText = 'position:fixed;top:16px;right:16px;z-index:2000;display:flex;flex-direction:column;gap:8px;max-width:360px;';
            document.body.appendChild(box);
        }
        var colors = { success: '#0f766e', danger: '#b91c1c', warning: '#b45309', info: '#1f6fb2' };
        var el = document.createElement('div');
        el.textContent = String(message);            // textContent: never inserts HTML
        el.style.cssText = 'background:' + (colors[type] || colors.info) +
            ';color:#fff;padding:12px 16px;border-radius:12px;font-size:14px;box-shadow:0 10px 24px rgba(15,31,61,.25);';
        box.appendChild(el);
        setTimeout(function () {
            el.style.transition = 'opacity .4s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 400);
        }, 3500);
    };

    /* Keyboard shortcut helper: MediGen.shortcut('F2', fn). Ignored while typing in a text box
       unless the key is an F-key (F-keys are safe to use anywhere). */
    MediGen.shortcut = function (key, fn) {
        document.addEventListener('keydown', function (e) {
            if (e.key !== key) return;
            e.preventDefault();
            fn(e);
        });
    };

    window.MediGen = MediGen;
})(window);

/* Forms inside a popup (modal): show the missing field as a message inside the popup.
   The browser's own bubble can appear off-screen inside a modal, so the user sees nothing and thinks Save is blocked. */
(function () {
    'use strict';
    document.addEventListener('invalid', function (e) {
        var field = e.target;
        var modal = field.closest && field.closest('.modal');
        if (!modal) return;                          // normal pages keep the browser's own message
        e.preventDefault();
        var body = modal.querySelector('.modal-body') || modal;
        var box = body.querySelector('.mg-form-err');
        if (!box) {
            box = document.createElement('div');
            box.className = 'alert alert-danger small mb-3 mg-form-err';
            box.setAttribute('role', 'alert');
            body.insertBefore(box, body.firstChild);
        }
        var row = field.closest('.mb-3, .form-group, .col-md-6, .col-12') || field.parentNode;
        var label = row && row.querySelector('label');
        var name = label ? label.textContent.replace('*', '').trim() : (field.name || 'a field');
        box.textContent = 'Please fill: ' + name + '.';
        box.hidden = false;
        field.focus();
    }, true);
    // hide the message again once the person starts correcting the form
    document.addEventListener('input', function (e) {
        var modal = e.target.closest && e.target.closest('.modal');
        var box = modal && modal.querySelector('.mg-form-err');
        if (box) box.hidden = true;
    });
})();

/* Popups (modals) are moved to the end of <body> once, so they always sit above the page overlay.
   Some page wrappers create their own stacking context, which can put the overlay above a popup. */
(function () {
    'use strict';
    function moveModals() {
        document.querySelectorAll('.modal').forEach(function (m) {
            if (m.parentNode !== document.body) document.body.appendChild(m);
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', moveModals);
    else moveModals();
})();
