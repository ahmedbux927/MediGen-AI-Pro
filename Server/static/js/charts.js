/* MediGen charts (v24): one look and one animation style for every chart in the app.
   Needs Chart.js 4 loaded first. Each chart is drawn only when it scrolls into view,
   so the animation is seen. Users with "reduce motion" on get the finished chart at once.

   MediCharts.weekBars(canvasId, labels, values)         dashboard: last 7 days revenue
   MediCharts.topDoughnut(canvasId, names, units)         dashboard: top sellers
   MediCharts.revenueLine(canvasId, labels, values)       reports: revenue trend (draw-in + timeline) */
(function (global) {
    'use strict';

    var TEAL = '#0f9aa0', NAVY = '#0b2a4a', INK = '#44546f', GRID = '#edf1f7';
    var SLICES = ['#0f9aa0', '#1f6fb2', '#5a64c8', '#a85f0a', '#5b6b84'];
    var FONT = "'Plus Jakarta Sans', 'Segoe UI', sans-serif";

    function hasChart() { return typeof global.Chart !== 'undefined'; }
    function reduced() {
        return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }
    // Animation switch shared with the dashboard (same localStorage key). Reduced-motion users start with it off.
    var ANIM_KEY = 'mgChartAnim';
    function animOn() {
        if (reduced()) return false;
        try { return global.localStorage.getItem(ANIM_KEY) !== '0'; } catch (e) { return true; }
    }
    function setAnimOn(on) {
        try { global.localStorage.setItem(ANIM_KEY, on ? '1' : '0'); } catch (e) { /* private mode: this page only */ }
    }
    function money(v) { return 'Rs. ' + Math.round(v).toLocaleString('en-PK'); }
    function sum(list) { return list.reduce(function (a, b) { return a + b; }, 0); }
    function anyPositive(list) { return list.some(function (v) { return v > 0; }); }

    function setDefaults() {
        Chart.defaults.font.family = FONT;
        Chart.defaults.color = INK;
    }

    // Gradient that follows the chart area, so it looks right at any width.
    function gradient(chart, from, to) {
        var area = chart.chartArea;
        if (!area) return to;
        var g = chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
        g.addColorStop(0, from);
        g.addColorStop(1, to);
        return g;
    }

    function tooltip(labelFn) {
        return {
            backgroundColor: NAVY, titleColor: '#ffffff', bodyColor: '#e6eef8',
            padding: 12, cornerRadius: 10, displayColors: false,
            titleFont: { size: 13, weight: '700' }, bodyFont: { size: 13 },
            callbacks: { label: labelFn }
        };
    }

    function emptyNote(canvas, text) {
        canvas.style.display = 'none';
        var p = document.createElement('p');
        p.className = 'chart-empty';
        p.textContent = text;
        canvas.parentNode.insertBefore(p, canvas);
    }

    // Run fn once, when the canvas is on screen (or straight away if the browser cannot tell).
    function whenVisible(el, fn) {
        if (!('IntersectionObserver' in global)) { fn(); return; }
        var io = new IntersectionObserver(function (entries) {
            if (entries[0].isIntersecting) { io.disconnect(); fn(); }
        }, { threshold: 0.3 });
        io.observe(el);
    }

    function canvasById(id) {
        var el = document.getElementById(id);
        return (el && hasChart()) ? el : null;
    }

    /* ---------- 1. Weekly revenue bars ---------- */
    function weekBars(id, labels, values) {
        var canvas = canvasById(id);
        if (!canvas) return;
        if (!anyPositive(values)) { emptyNote(canvas, 'No sales in the last 7 days yet.'); return; }
        setDefaults();
        whenVisible(canvas, function () {
            var top = Math.max.apply(null, values);
            new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Revenue',
                        data: values,
                        backgroundColor: function (c) { return gradient(c.chart, 'rgba(15,154,160,0.95)', 'rgba(31,111,178,0.80)'); },
                        hoverBackgroundColor: function (c) { return gradient(c.chart, '#14b3ba', '#2f83c9'); },
                        borderRadius: 10, borderSkipped: false, maxBarThickness: 56
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: !animOn() ? false : {
                        duration: 1000,
                        easing: 'easeOutQuart',
                        delay: function (ctx) {
                            return (ctx.type === 'data' && ctx.mode === 'default') ? ctx.dataIndex * 90 : 0;
                        }
                    },
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: tooltip(function (c) { return 'Revenue: ' + money(c.parsed.y); })
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            suggestedMax: top * 1.15,
                            ticks: { font: { size: 12, weight: 'bold' }, callback: function (v) { return money(v); } },
                            grid: { color: GRID }
                        },
                        x: { ticks: { font: { size: 12, weight: 'bold' } }, grid: { display: false } }
                    }
                }
            });
        });
    }

    /* ---------- 2. Top sellers doughnut ---------- */
    var centreLabel = {
        id: 'centreLabel',
        afterDraw: function (chart) {
            var meta = chart.getDatasetMeta(0);
            if (!meta || !meta.data || !meta.data[0]) return;
            var arc = meta.data[0];
            var total = sum(chart.data.datasets[0].data);
            var ctx = chart.ctx;
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = NAVY;
            ctx.font = '800 22px ' + FONT;
            ctx.fillText(total.toLocaleString('en-PK'), arc.x, arc.y - 8);
            ctx.fillStyle = INK;
            ctx.font = '600 12px ' + FONT;
            ctx.fillText('units sold', arc.x, arc.y + 14);
            ctx.restore();
        }
    };

    function topDoughnut(id, names, units) {
        var canvas = canvasById(id);
        if (!canvas) return;
        if (!anyPositive(units)) { emptyNote(canvas, 'No sales recorded yet.'); return; }
        setDefaults();
        whenVisible(canvas, function () {
            new Chart(canvas, {
                type: 'doughnut',
                plugins: [centreLabel],
                data: {
                    labels: names,
                    datasets: [{
                        data: units,
                        backgroundColor: SLICES,
                        borderColor: '#ffffff',
                        borderWidth: 3,
                        spacing: 3,
                        borderRadius: 6,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '66%',
                    animation: !animOn() ? false : {
                        animateRotate: true,
                        animateScale: false,
                        duration: 1200,
                        easing: 'easeOutCubic'
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12 } }
                        },
                        tooltip: tooltip(function (c) {
                            var total = sum(c.dataset.data);
                            var pct = total ? Math.round(c.parsed / total * 100) : 0;
                            return c.label + ': ' + c.parsed + ' sold (' + pct + '%)';
                        })
                    }
                }
            });
        });
    }

    /* ---------- 3. Revenue trend line (reports) ---------- */
    // Each point is drawn in turn, left to right, then the line settles.
    function drawInAnimation(n) {
        var step = Math.max(40, Math.min(160, Math.round(1400 / Math.max(n, 1))));
        function previousY(ctx) {
            if (ctx.index === 0) return ctx.chart.scales.y.getPixelForValue(0);
            return ctx.chart.getDatasetMeta(ctx.datasetIndex).data[ctx.index - 1].getProps(['y'], true).y;
        }
        return {
            x: {
                type: 'number', easing: 'linear', duration: step, from: NaN,
                delay: function (ctx) {
                    if (ctx.type !== 'data' || ctx.xStarted) return 0;
                    ctx.xStarted = true;
                    return ctx.index * step;
                }
            },
            y: {
                type: 'number', easing: 'easeOutQuart', duration: step * 2, from: previousY,
                delay: function (ctx) {
                    if (ctx.type !== 'data' || ctx.yStarted) return 0;
                    ctx.yStarted = true;
                    return ctx.index * step;
                }
            }
        };
    }

    function revenueLine(id, labels, values, opts) {
        opts = opts || {};
        var canvas = canvasById(id);
        if (!canvas) return;
        if (!anyPositive(values)) { emptyNote(canvas, 'No sales in this period.'); return; }
        setDefaults();

        var n = values.length;
        var peak = Math.max.apply(null, values);
        var card = canvas.closest('.chart-card');
        var chart = null;
        var shown = n;           // how many points are visible (timeline uses this)
        var timer = null;

        function data(count) {
            return labels.map(function (_, k) { return k < count ? values[k] : null; });
        }

        function create() {
            chart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Revenue',
                        data: values,
                        borderColor: TEAL,
                        borderWidth: 3,
                        tension: 0.35,
                        fill: true,
                        backgroundColor: function (c) { return gradient(c.chart, 'rgba(15,154,160,0.40)', 'rgba(15,154,160,0.02)'); },
                        pointBackgroundColor: TEAL,
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: function (c) { return c.dataIndex === n - 1 ? 6 : 3; },
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    animation: !animOn() ? false : drawInAnimation(n),
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: tooltip(function (c) { return 'Revenue: ' + money(c.parsed.y); })
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: peak * 1.15,              // fixed scale: the line grows, the axis does not jump
                            ticks: { font: { size: 11, weight: 'bold' }, callback: function (v) { return money(v); } },
                            grid: { color: GRID }
                        },
                        x: { ticks: { font: { size: 11, weight: 'bold' }, maxRotation: 0, autoSkip: true }, grid: { display: false } }
                    }
                }
            });
        }

        // The draw-in plays when the card is on screen; reduced-motion users get the finished line.
        if (!animOn()) create();
        else whenVisible(card || canvas, create);

        function replay() {
            if (!chart) return;
            stopTimeline();
            chart.options.animation = animOn() ? drawInAnimation(n) : false;
            chart.data.datasets[0].data = data(0);
            chart.update('none');
            chart.data.datasets[0].data = values;
            chart.update();
        }

        function stopTimeline() {
            if (timer) { clearInterval(timer); timer = null; }
        }

        // Timeline: reveal one day at a time, with a running total.
        function timeline() {
            if (!chart) return;
            if (timer) { stopTimeline(); setButtons(); return; }
            if (shown >= n) shown = 0;
            chart.options.animation = false;
            timer = setInterval(function () {
                shown += 1;
                chart.data.datasets[0].data = data(shown);
                chart.update('none');
                readout();
                if (shown >= n) { stopTimeline(); setButtons(); }
            }, 450);
            setButtons();
        }

        var bar = null, replayBtn = null, timelineBtn = null, totalEl = null, animBtn = null;
        function paintAnim() {
            if (!animBtn) return;
            var on = animOn();
            animBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
            animBtn.innerHTML = on ? '<i class="bi bi-lightning-charge-fill"></i> Animate: on' : '<i class="bi bi-lightning-charge"></i> Animate: off';
            animBtn.disabled = reduced();
            animBtn.title = reduced() ? 'Your device asks for reduced motion' : '';
        }
        function toggleAnim() {
            if (reduced()) return;
            setAnimOn(!animOn());
            paintAnim();
            if (timer) { clearInterval(timer); timer = null; setButtons(); }
            if (chart) { chart.destroy(); chart = null; }
            shown = n;
            create();
            readout();
        }
        function readout() {
            if (!totalEl) return;
            var s = 0;
            for (var k = 0; k < shown; k++) s += values[k];
            totalEl.textContent = (shown < n ? labels[shown - 1] + ' · ' : '') + 'running total ' + money(s);
        }
        function setButtons() {
            if (!timelineBtn) return;
            timelineBtn.innerHTML = timer ? '<i class="bi bi-pause-fill"></i> Pause' : '<i class="bi bi-play-fill"></i> Timeline';
        }

        function addControls() {
            if (!card) return;
            bar = document.createElement('div');
            bar.className = 'rv-toolbar';
            bar.innerHTML =
                '<button type="button" class="rv-btn" data-act="replay" aria-label="Replay the chart"><i class="bi bi-arrow-clockwise"></i> Replay</button>' +
                '<button type="button" class="rv-btn" data-act="timeline" aria-label="Play day by day"><i class="bi bi-play-fill"></i> Timeline</button>' +
                '<button type="button" class="rv-btn" data-act="anim" role="switch" aria-label="Chart animations"></button>' +
                '<span class="rv-readout" id="rvTotal"></span>';
            var heading = card.querySelector('h5');
            if (heading && heading.parentNode) heading.parentNode.insertBefore(bar, heading.nextSibling);
            else canvas.parentNode.insertBefore(bar, canvas);
            replayBtn = bar.querySelector('[data-act="replay"]');
            timelineBtn = bar.querySelector('[data-act="timeline"]');
            totalEl = bar.querySelector('#rvTotal');
            animBtn = bar.querySelector('[data-act="anim"]');
            animBtn.addEventListener('click', toggleAnim);
            paintAnim();
            replayBtn.addEventListener('click', function () { replay(); readout(); });
            timelineBtn.addEventListener('click', timeline);
            readout();
        }

        addControls();
    }

    global.MediCharts = {
        weekBars: weekBars,
        topDoughnut: topDoughnut,
        revenueLine: revenueLine,
        animationOn: animOn
    };
})(window);
