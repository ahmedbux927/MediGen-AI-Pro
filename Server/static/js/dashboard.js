/* Dashboard behaviour (v52): greeting, live clock, count-up numbers and charts.
   Charts read their colours from the page theme, so dark / light switching recolours them.
   Everything degrades to the server-rendered numbers if JavaScript or Chart.js is unavailable. */
(function () {
    'use strict';

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var root = document.querySelector('.dash');
    if (!root) return;

    function cssVar(name) {
        return getComputedStyle(root).getPropertyValue(name).trim();
    }
    function hexToRgba(hex, a) {
        var h = hex.replace('#', '');
        if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
        var n = parseInt(h, 16);
        return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
    }
    function fmt(n) { return Number(n).toLocaleString('en-US'); }
    function nums(arr) { return (arr || []).map(function (v) { return Number(v) || 0; }); }

    /* ---------- Greeting and clock ---------- */
    var hello = document.getElementById('dHello');
    var dateEl = document.getElementById('dDate');
    var timeEl = document.getElementById('dTime');
    function tickClock() {
        var now = new Date();
        var h = now.getHours();
        var word = h < 12 ? 'Good morning' : (h < 17 ? 'Good afternoon' : 'Good evening');
        if (hello) hello.textContent = word;
        if (dateEl) dateEl.textContent = now.toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
        if (timeEl) timeEl.textContent = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    }
    tickClock();
    setInterval(tickClock, 30000);

    /* ---------- Count-up numbers ---------- */
    function countUp(el) {
        var end = Number(el.getAttribute('data-count')) || 0;
        if (reduce || end === 0) return;
        var dur = 1200;
        var start = performance.now();
        el.textContent = '0';
        function step(now) {
            var p = Math.min((now - start) / dur, 1);
            var e = 1 - Math.pow(1 - p, 4);
            el.textContent = fmt(Math.round(end * e));
            if (p < 1) requestAnimationFrame(step);
            else el.textContent = fmt(end);
        }
        requestAnimationFrame(step);
    }
    var counters = root.querySelectorAll('[data-count]');
    for (var i = 0; i < counters.length; i++) countUp(counters[i]);

    /* ---------- Charts ---------- */
    var data = null;
    try { data = JSON.parse(document.getElementById('dash-data').textContent); } catch (e) { data = null; }
    /* Charts need data and Chart.js. The animation switch still works without them. */
    var canChart = !!(data && data.hasData && typeof Chart !== 'undefined');

    var salesChart = null, sparkRev = null, sparkInv = null;

    /* Animation switch: remembered per browser (localStorage). Reduced-motion users start with it off. */
    var ANIM_KEY = 'mgChartAnim';
    function animPref() {
        if (reduce) return false;
        try { return localStorage.getItem(ANIM_KEY) !== '0'; } catch (e) { return true; }
    }
    var animOn = animPref();
    function animOpts(ms) {
        return animOn ? { duration: ms, easing: 'easeOutQuart' } : false;
    }

    function areaFill(color, top) {
        return function (ctx) {
            var area = ctx.chart.chartArea;
            if (!area) return 'transparent';
            var g = ctx.chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
            g.addColorStop(0, hexToRgba(color, top));
            g.addColorStop(1, hexToRgba(color, 0));
            return g;
        };
    }

    function labelsFor(days) {
        return days.map(function (d) {
            var p = d.split('-');
            return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2])).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
        });
    }

    function sparkline(id, values, color) {
        var el = document.getElementById(id);
        if (!el) return null;
        return new Chart(el, {
            type: 'line',
            data: {
                labels: values.map(function (_, idx) { return idx; }),
                datasets: [{
                    data: values,
                    borderColor: color,
                    borderWidth: 2,
                    backgroundColor: areaFill(color, 0.28),
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                events: [],
                animation: animOpts(1000),
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false, beginAtZero: true } }
            }
        });
    }

    function buildCharts() {
        var teal = cssVar('--d-teal') || '#0f9aa0';
        var blue = cssVar('--d-blue') || '#1f6fb2';
        var line = cssVar('--d-line') || '#e4ebf4';
        var ink3 = cssVar('--d-ink3') || '#7d8ba3';
        var card = cssVar('--d-card') || '#ffffff';
        var revenue = nums(data.revenue);
        var invoices = nums(data.invoices);

        var salesEl = document.getElementById('salesChart');
        if (salesEl) {
            salesChart = new Chart(salesEl, {
                type: 'line',
                data: {
                    labels: labelsFor(data.days),
                    datasets: [
                        {
                            label: 'Revenue (Rs.)',
                            data: revenue,
                            yAxisID: 'y',
                            borderColor: teal,
                            borderWidth: 2.5,
                            backgroundColor: areaFill(teal, 0.3),
                            fill: true,
                            tension: 0.38,
                            pointRadius: 3.5,
                            pointHoverRadius: 6,
                            pointBackgroundColor: card,
                            pointBorderColor: teal,
                            pointBorderWidth: 2
                        },
                        {
                            label: 'Invoices',
                            data: invoices,
                            yAxisID: 'y1',
                            borderColor: blue,
                            borderWidth: 2,
                            borderDash: [6, 4],
                            backgroundColor: 'transparent',
                            fill: false,
                            tension: 0.38,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            pointBackgroundColor: blue,
                            pointBorderColor: blue
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    animation: animOpts(1200),
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            displayColors: false,
                            padding: 10,
                            callbacks: {
                                label: function (c) {
                                    return c.dataset.yAxisID === 'y'
                                        ? 'Revenue: Rs. ' + fmt(c.parsed.y)
                                        : 'Invoices: ' + fmt(c.parsed.y);
                                }
                            }
                        }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: ink3, maxRotation: 0, autoSkip: true } },
                        y: {
                            beginAtZero: true,
                            position: 'left',
                            grid: { color: line, drawTicks: false },
                            border: { display: false },
                            ticks: {
                                color: ink3,
                                padding: 8,
                                callback: function (v) { return v >= 1000 ? (v / 1000) + 'k' : v; }
                            }
                        },
                        y1: {
                            beginAtZero: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            border: { display: false },
                            ticks: { color: blue, precision: 0, padding: 8 }
                        }
                    }
                }
            });
        }

        sparkRev = sparkline('dSparkRev', revenue, teal);
        sparkInv = sparkline('dSparkInv', invoices, blue);
    }

    /* Recolour the sales chart when the theme switch changes data-theme on <html>. */
    function recolour() {
        if (!salesChart) return;
        var line = cssVar('--d-line');
        var ink3 = cssVar('--d-ink3');
        var card = cssVar('--d-card');
        var blue = cssVar('--d-blue');
        var o = salesChart.options.scales;
        o.y.grid.color = line;
        o.x.ticks.color = ink3;
        o.y.ticks.color = ink3;
        o.y1.ticks.color = blue;
        salesChart.data.datasets[0].pointBackgroundColor = card;
        salesChart.data.datasets[1].borderColor = blue;
        salesChart.data.datasets[1].pointBackgroundColor = blue;
        salesChart.data.datasets[1].pointBorderColor = blue;
        salesChart.update('none');
    }

    function destroyCharts() {
        if (salesChart) { salesChart.destroy(); salesChart = null; }
        if (sparkRev) { sparkRev.destroy(); sparkRev = null; }
        if (sparkInv) { sparkInv.destroy(); sparkInv = null; }
    }

    /* Switch: flip the preference, save it, and redraw so the change is visible at once. */
    var toggle = document.getElementById('dAnimToggle');
    function paintToggle() {
        if (!toggle) return;
        toggle.setAttribute('aria-checked', animOn ? 'true' : 'false');
        toggle.classList.toggle('is-on', animOn);
        toggle.disabled = reduce;
        toggle.title = reduce ? 'Your device asks for reduced motion' : '';
    }
    if (toggle) {
        paintToggle();
        toggle.addEventListener('click', function () {
            if (reduce) return;
            animOn = !animOn;
            try { localStorage.setItem(ANIM_KEY, animOn ? '1' : '0'); } catch (e) { /* private mode: keep it for this page only */ }
            paintToggle();
            destroyCharts();
            if (canChart) buildCharts();
        });
    }

    if (canChart) buildCharts();
    new MutationObserver(recolour).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
