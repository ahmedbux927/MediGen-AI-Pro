/* Glowing Edge Card behaviour: follows the pointer and plays a short intro sweep.
   Works with every element that has class "glow-card". Respects prefers-reduced-motion. */
(function () {
    'use strict';

    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function clamp(v, min, max) { return Math.min(Math.max(v, min), max); }
    function round(v, p) { return parseFloat(v.toFixed(p || 3)); }

    function angleFrom(dx, dy) {
        if (dx === 0 && dy === 0) return 0;
        var a = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
        return a < 0 ? a + 360 : a;
    }

    // 1 at the edge, 0 at the centre.
    function closenessToEdge(cx, cy, x, y) {
        var dx = x - cx, dy = y - cy;
        var kx = dx !== 0 ? cx / Math.abs(dx) : Infinity;
        var ky = dy !== 0 ? cy / Math.abs(dy) : Infinity;
        return clamp(1 / Math.min(kx, ky), 0, 1);
    }

    function init(card) {
        var animating = false;
        var startTimer = 0;
        var frame = 0;

        function stopIntro() {
            if (!animating) return;
            animating = false;
            cancelAnimationFrame(frame);
            clearTimeout(startTimer);
            card.classList.remove('animating');
        }

        function onMove(e) {
            var r = card.getBoundingClientRect();
            if (!r.width || !r.height) return;
            var x = e.clientX - r.left, y = e.clientY - r.top;
            var cx = r.width / 2, cy = r.height / 2;
            var dx = x - cx, dy = y - cy;

            card.style.setProperty('--pointer-x', round(clamp(100 / r.width * x, 0, 100)) + '%');
            card.style.setProperty('--pointer-y', round(clamp(100 / r.height * y, 0, 100)) + '%');
            card.style.setProperty('--pointer-deg', round(angleFrom(dx, dy)) + 'deg');
            card.style.setProperty('--pointer-d', round(closenessToEdge(cx, cy, x, y) * 100));
            stopIntro();
        }

        // Intro sweep timeline (ms): glow fades in 500-1000, rotates 500-4250, fades out 3000-4500.
        function playIntro() {
            if (!card.isConnected) return;
            animating = true;
            card.classList.add('animating');
            var a0 = 110, a1 = 465;
            card.style.setProperty('--pointer-deg', a0 + 'deg');
            var t0 = performance.now();

            function step(now) {
                if (!animating) return;
                var el = now - t0;
                var d, deg;
                if (el > 500 && el < 1000) {
                    var t = (el - 500) / 500;
                    card.style.setProperty('--pointer-d', String((1 - Math.pow(1 - t, 3)) * 100));
                }
                if (el > 500 && el < 2000) {
                    var u = (el - 500) / 1500;
                    deg = (a1 - a0) * (u * u * u * 0.5) + a0;
                    card.style.setProperty('--pointer-deg', deg + 'deg');
                }
                if (el >= 2000 && el < 4250) {
                    var w = (el - 2000) / 2250;
                    deg = (a1 - a0) * (0.5 + (1 - Math.pow(1 - w, 3)) * 0.5) + a0;
                    card.style.setProperty('--pointer-deg', deg + 'deg');
                }
                if (el > 3000 && el < 4500) {
                    var s = (el - 3000) / 1500;
                    card.style.setProperty('--pointer-d', String((1 - s * s * s) * 100));
                }
                if (el < 4500) {
                    frame = requestAnimationFrame(step);
                } else {
                    stopIntro();
                }
            }
            frame = requestAnimationFrame(step);
        }

        card.addEventListener('pointermove', onMove);
        card.addEventListener('pointerdown', stopIntro);
        if (!reduceMotion) {
            startTimer = setTimeout(playIntro, 500);
        }
    }

    function boot() {
        var cards = document.querySelectorAll('.glow-card');
        for (var i = 0; i < cards.length; i++) {
            if (!cards[i].dataset.glowReady) {
                cards[i].dataset.glowReady = '1';
                init(cards[i]);
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
