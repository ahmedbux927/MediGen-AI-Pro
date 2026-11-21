/* v86.51: voice search for the medicine search boxes.
   A button with data-voice-for="<input id>" listens once and puts the spoken words in the box,
   then fires an input event so the live filter runs. Hidden when the browser cannot listen,
   which is the case on plain http from a phone (microphone needs localhost or https). */
(function () {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;

    function listen(btn) {
        var input = document.getElementById(btn.getAttribute('data-voice-for'));
        if (!input) return;
        var rec = new SR();
        rec.lang = 'en-IN';          /* English names and Indian accent; Urdu script is not matched to English medicine names */
        rec.interimResults = false;
        rec.maxAlternatives = 1;
        btn.classList.add('listening');
        btn.title = 'Listening...';
        rec.onresult = function (e) {
            var text = (e.results[0] && e.results[0][0].transcript || '').trim();
            input.value = text;
            input.dispatchEvent(new Event('input', { bubbles: true }));
        };
        rec.onerror = function (e) {
            btn.title = 'No speech detected (' + (e.error || 'error') + '). Press again.';
        };
        rec.onend = function () {
            btn.classList.remove('listening');
            if (!btn.title || btn.title === 'Listening...') btn.title = 'Speak to search';
            input.focus();
        };
        try { rec.start(); } catch (err) { btn.classList.remove('listening'); btn.title = 'The microphone could not start yet.'; }
    }

    function setup() {
        var buttons = document.querySelectorAll('[data-voice-for]');
        var supported = !!SR && !!window.isSecureContext;
        buttons.forEach(function (btn) {
            if (!supported) { btn.hidden = true; return; }
            btn.title = 'Speak to search';
            btn.addEventListener('click', function () { listen(btn); });
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
    else setup();
})();
