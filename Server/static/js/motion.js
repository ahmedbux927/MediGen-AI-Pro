/* MediGen motion, sound and the "Animation & sound" panel (v87.17).
   Settings are per device (stored in this browser). Defaults: sound off, speed 1, strength 1, volume 0.5.
   Storage and audio calls are wrapped; the page works without them. */
(function () {
  var KEY = 'mgMotion';
  var DEFAULTS = { sound: false, volume: 0.5, speed: 1, strength: 1 };
  var cfg = load();
  var ctx = null;

  function load() {
    var out = {};
    for (var k in DEFAULTS) out[k] = DEFAULTS[k];
    try {
      var saved = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (saved) for (var j in DEFAULTS) if (saved[j] != null) out[j] = saved[j];
    } catch (e) { }
    return out;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(cfg)); } catch (e) { }
  }
  function apply() {
    var root = document.documentElement.style;
    root.setProperty('--mg-speed', String(cfg.speed));
    root.setProperty('--mg-strength', String(cfg.strength));
  }

  function audio() {
    if (ctx) return ctx;
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    try { ctx = new AC(); } catch (e) { ctx = null; }
    return ctx;
  }
  function chime(freq, when, dur, vol) {
    var a = audio();
    if (!a) return;
    var o = a.createOscillator();
    var g = a.createGain();
    var peak = Math.max(0.0002, vol * cfg.volume);
    o.type = 'sine';
    o.frequency.value = freq;
    g.gain.setValueAtTime(0.0001, a.currentTime + when);
    g.gain.exponentialRampToValueAtTime(peak, a.currentTime + when + 0.04);
    g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + when + dur);
    o.connect(g); g.connect(a.destination);
    o.start(a.currentTime + when);
    o.stop(a.currentTime + when + dur + 0.05);
  }
  function play(kind) {
    if (!cfg.sound || cfg.volume <= 0) return;
    try {
      if (ctx && ctx.state === 'suspended') ctx.resume();
      if (kind === 'ok') { chime(660, 0, 0.5, 0.05); chime(990, 0.12, 0.6, 0.035); }
      else { chime(523, 0, 0.6, 0.04); }
    } catch (e) { }
  }
  window.mgChime = play;

  /* ---------- Top-bar button and panel ---------- */
  function addButton() {
    var meta = document.querySelector('.top-meta');
    if (!meta || meta.querySelector('.sound-toggle')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-toggle sound-toggle';
    btn.setAttribute('aria-haspopup', 'dialog');
    btn.innerHTML = '<i class="bi bi-sliders"></i> <span class="sound-label">Animation &amp; sound</span>';
    btn.addEventListener('click', function (e) { e.stopPropagation(); togglePanel(btn); });
    meta.insertBefore(btn, meta.firstChild);
  }

  var panel = null;
  function togglePanel(btn) {
    if (panel) { closePanel(); return; }
    panel = document.createElement('div');
    panel.className = 'mg-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Animation and sound');
    panel.innerHTML =
      '<h6>Animation &amp; sound</h6>' +
      '<div class="mg-sub">Is device ke liye. Dono browser mein save hote hain.</div>' +
      row('mgSpeed', 'Speed', 'speed', 0.5, 2, 0.1, cfg.speed, 'x') +
      row('mgStrength', 'Strength', 'strength', 0, 2, 0.1, cfg.strength, '') +
      row('mgVolume', 'Sound volume', 'volume', 0, 1, 0.05, cfg.volume, '%') +
      '<label class="mg-check"><input type="checkbox" id="mgSound"' + (cfg.sound ? ' checked' : '') + '> Sound on</label>' +
      '<div class="mg-actions"><button type="button" class="mg-test" id="mgTest">Test sound</button>' +
      '<button type="button" class="btn-ghost" id="mgReset">Reset</button></div>';
    document.body.appendChild(panel);
    bind();
    btn.setAttribute('aria-expanded', 'true');
    setTimeout(function () { document.addEventListener('click', outside); }, 0);
  }
  function row(id, label, key, min, max, step, val, unit) {
    var shown = key === 'volume' ? Math.round(val * 100) + '%' : (key === 'speed' ? val + 'x' : val);
    return '<div class="mg-row"><label for="' + id + '">' + label + '</label>' +
      '<output id="' + id + 'Out">' + shown + '</output>' +
      '<input type="range" id="' + id + '" min="' + min + '" max="' + max + '" step="' + step + '" value="' + val + '"></div>';
  }
  function bind() {
    var map = [['mgSpeed', 'speed', function (v) { return v + 'x'; }],
               ['mgStrength', 'strength', function (v) { return v; }],
               ['mgVolume', 'volume', function (v) { return Math.round(v * 100) + '%'; }]];
    map.forEach(function (m) {
      var input = document.getElementById(m[0]);
      input.addEventListener('input', function () {
        cfg[m[1]] = parseFloat(input.value);
        document.getElementById(m[0] + 'Out').textContent = m[2](cfg[m[1]]);
        apply(); save();
      });
    });
    document.getElementById('mgSound').addEventListener('change', function (e) {
      cfg.sound = e.target.checked;
      save();
      if (cfg.sound) { audio(); play('ok'); }
    });
    document.getElementById('mgTest').addEventListener('click', function () {
      var was = cfg.sound; cfg.sound = true; play('ok'); cfg.sound = was;
    });
    document.getElementById('mgReset').addEventListener('click', function () {
      for (var k in DEFAULTS) cfg[k] = DEFAULTS[k];
      apply(); save(); closePanel(); togglePanel(document.querySelector('.sound-toggle'));
    });
  }
  function outside(e) {
    if (panel && !panel.contains(e.target) && !e.target.closest('.sound-toggle')) closePanel();
  }
  function closePanel() {
    if (panel) panel.remove();
    panel = null;
    document.removeEventListener('click', outside);
    var btn = document.querySelector('.sound-toggle');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  /* ---------- Soft fade before sidebar links ---------- */
  function wireLeave() {
    var nav = document.getElementById('sideNav');
    if (!nav) return;
    nav.addEventListener('click', function (e) {
      var a = e.target.closest('a[href]');
      if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
      if (a.hasAttribute('data-ai-open')) return;
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#') return;
      if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      e.preventDefault();
      document.body.classList.add('mg-leaving');
      var ms = Math.round(170 / cfg.speed);
      setTimeout(function () { window.location.href = href; }, ms);
      play('soft');
    });
  }

  function init() {
    apply();
    addButton();
    wireLeave();
    if (document.querySelector('.alert-success')) play('ok');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
