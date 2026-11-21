/* MediGen AI assistant (v53).
   - Slides in from the right. Opened from the sidebar item, Quick actions, the floating button,
     and automatically on each dashboard load (after login or reload).
   - Closes by itself only after 30 seconds with NO activity: no pointer or key input, no question
     waiting for an answer, and no unsent text. Any activity restarts the 30 seconds.
   - Manual close: the X button, Esc, or (on phones) tapping the shade.
   - Answers come from the existing /chatbot/api route, the same engine as the Chatbot page. */
(function () {
    'use strict';

    var panel = document.getElementById('aiPanel');
    if (!panel) return;

    var API = '/chatbot/api';
    var IDLE_MS = 30000;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var fab = document.getElementById('aiFab');
    var closeBtn = document.getElementById('aiClose');
    var msgs = document.getElementById('aiMessages');
    var form = document.getElementById('aiForm');
    var input = document.getElementById('aiInput');
    var sendBtn = form.querySelector('.ai-send');
    var hello = document.getElementById('aiHello');
    var quick = document.getElementById('aiQuick');

    var isOpen = false;
    var busy = false;
    var idleTimer = null;

    /* Mobile shade: created here so the markup stays simple. */
    var shade = document.createElement('div');
    shade.className = 'ai-shade';
    shade.setAttribute('aria-hidden', 'true');
    document.body.appendChild(shade);

    function esc(t) {
        return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    /* Same light formatting as the Chatbot page: **bold** and *click to try* */
    function fmt(t) {
        return esc(t)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<span class="try" data-q="$1">$1</span>');
    }
    function csrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.content : '';
    }
    function scrollDown() { msgs.scrollTop = msgs.scrollHeight; }

    /* ---------- Idle auto-close ---------- */
    function hasDraft() { return input.value.trim().length > 0; }
    function clearIdle() { clearTimeout(idleTimer); idleTimer = null; }
    function armIdle() {
        clearIdle();
        if (!isOpen) return;
        idleTimer = setTimeout(onIdle, IDLE_MS);
    }
    function onIdle() {
        idleTimer = null;
        if (!isOpen) return;
        /* Still working: a question is being answered or the user has typed something. Keep it open. */
        if (busy || hasDraft()) { armIdle(); return; }
        close(false);
    }
    function touch() { if (isOpen) armIdle(); }

    /* ---------- Open / close ---------- */
    function open(byUser) {
        if (isOpen) { touch(); if (byUser) input.focus(); return; }
        isOpen = true;
        panel.classList.add('open');
        shade.classList.add('open');
        panel.setAttribute('aria-hidden', 'false');
        fab.setAttribute('aria-expanded', 'true');
        armIdle();
        if (byUser) setTimeout(function () { input.focus({ preventScroll: true }); }, 380);
    }
    function close(byUser) {
        if (!isOpen) return;
        isOpen = false;
        clearIdle();
        panel.classList.remove('open');
        shade.classList.remove('open');
        panel.setAttribute('aria-hidden', 'true');
        fab.setAttribute('aria-expanded', 'false');
        if (byUser && panel.contains(document.activeElement)) fab.focus({ preventScroll: true });
    }

    /* ---------- Messages ---------- */
    function addMsg(text, who) {
        var row = document.createElement('div');
        row.className = 'ai-msg ' + (who === 'user' ? 'user' : 'bot');
        var dot = document.createElement('span');
        dot.className = 'ai-dot';
        if (who === 'user') dot.textContent = 'You';
        else dot.innerHTML = '<svg viewBox="0 0 120 120" width="18" height="18" aria-hidden="true"><use href="#aiRobotArt"/></svg>';
        var bubble = document.createElement('div');
        bubble.className = 'ai-bubble';
        if (who === 'user') bubble.textContent = text;
        else bubble.innerHTML = fmt(text);
        row.append(dot, bubble);
        msgs.appendChild(row);
        scrollDown();
        return row;
    }
    function addTyping() {
        var row = document.createElement('div');
        row.className = 'ai-msg bot';
        row.innerHTML = '<span class="ai-dot"><svg viewBox="0 0 120 120" width="18" height="18" aria-hidden="true"><use href="#aiRobotArt"/></svg></span>' +
            '<div class="ai-bubble"><span class="ai-typing"><i></i><i></i><i></i></span></div>';
        msgs.appendChild(row);
        scrollDown();
        return row;
    }

    /* ---------- Sending ---------- */
    function send(text) {
        text = String(text || '').trim();
        if (!text || busy) return;
        busy = true;
        sendBtn.disabled = true;
        addMsg(text, 'user');
        input.value = '';
        armIdle();
        var typing = addTyping();

        fetch(API, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
            body: JSON.stringify({ question: text })
        })
            .then(function (r) {
                return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, d: d }; });
            })
            .then(function (res) {
                typing.remove();
                if (res.ok && res.d.answer) addMsg(res.d.answer, 'bot');
                else addMsg(res.d.error || 'Something went wrong. Please try again.', 'bot');
            })
            .catch(function () {
                typing.remove();
                addMsg('The assistant is unavailable right now. Please try again.', 'bot');
            })
            .then(function () {
                busy = false;
                sendBtn.disabled = false;
                armIdle();
            });
    }

    /* ---------- Wiring ---------- */
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        send(input.value);
    });
    msgs.addEventListener('click', function (e) {
        var t = e.target.closest('.try');
        if (t) send(t.getAttribute('data-q'));
    });
    quick.addEventListener('click', function (e) {
        var b = e.target.closest('button[data-q]');
        if (b) { open(false); send(b.getAttribute('data-q')); }
    });
    document.querySelectorAll('[data-ai-open]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            /* Sidebar link: stay on this page and slide the panel in. Without JS the link still goes to the Chatbot page. */
            e.preventDefault();
            open(true);
        });
    });
    closeBtn.addEventListener('click', function () { close(true); });
    shade.addEventListener('click', function () { close(true); });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isOpen) close(true);
    });

    /* Any real activity inside the panel keeps it open. */
    ['pointermove', 'pointerdown', 'keydown', 'focusin', 'wheel', 'touchmove'].forEach(function (ev) {
        panel.addEventListener(ev, touch, { passive: true });
    });

    /* Greeting uses the logged-in user's name from the template. */
    var name = panel.getAttribute('data-name') || '';
    var h = new Date().getHours();
    var part = h < 12 ? 'Good morning' : (h < 17 ? 'Good afternoon' : 'Good evening');
    if (hello) hello.textContent = part + (name ? ', ' + name : '') + '!';

    /* Dashboard: open on every load (login redirect or reload) on desktop. On phones the panel covers the
       whole screen, so it stays closed until the person opens it. Other pages open only on request. */
    var phone = !!(window.matchMedia && window.matchMedia('(max-width: 520px)').matches);
    if (panel.getAttribute('data-autoopen') === '1' && !phone) {
        setTimeout(function () { open(false); }, reduce ? 0 : 700);
    }
})();
