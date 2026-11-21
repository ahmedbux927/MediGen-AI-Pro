/* MediGen barcode scanner (v75): reads barcodes with the phone or PC camera.
   Uses the browser's built-in BarcodeDetector (Chrome, Edge, Android). Where it is missing
   (iPhone Safari, Firefox) it loads the ZXing reader once, from jsdelivr, and uses that instead.
   Needs a secure connection (https, or the PC itself at 127.0.0.1) because browsers block the camera on plain http.
   If the camera cannot be used at all, the user types the code or uses a USB/Bluetooth scanner.

   MediScan.open({ onCode: fn, keepOpen: bool, onClose: fn })  opens the camera
   MediScan.fillFrom(button)   scans into the input next to the button (medicine form)  */
(function (global) {
    'use strict';
    var FORMATS = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128', 'code_39', 'qr_code'];
    var ZXING_URL = 'https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js';
    var zxingPromise = null;

    function nativeSupported() {
        return !!(global.BarcodeDetector && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
    function cameraSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }
    function barcodeSupported() { return nativeSupported() || cameraSupported(); }

    /* Loads ZXing only when needed. Resolves with the ZXing global, or rejects. */
    function loadZxing() {
        if (global.ZXing && global.ZXing.BrowserMultiFormatReader) return Promise.resolve(global.ZXing);
        if (!zxingPromise) {
            zxingPromise = new Promise(function (resolve, reject) {
                var s = document.createElement('script');
                s.src = ZXING_URL;
                s.async = true;
                s.onload = function () {
                    if (global.ZXing && global.ZXing.BrowserMultiFormatReader) resolve(global.ZXing);
                    else { zxingPromise = null; reject(new Error('zxing not ready')); }
                };
                s.onerror = function () { zxingPromise = null; reject(new Error('zxing load failed')); };
                document.head.appendChild(s);
            });
        }
        return zxingPromise;
    }

    function open(opts) {
        opts = opts || {};
        var overlay = document.createElement('div');
        overlay.className = 'scan-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-label', 'Barcode scanner');
        overlay.innerHTML =
            '<div class="scan-box"><video playsinline muted></video><div class="scan-frame" aria-hidden="true"></div></div>' +
            '<div class="scan-msg" aria-live="polite">Starting camera...</div>' +
            '<button type="button" class="scan-close"><i class="bi bi-x-lg"></i> Close</button>';
        document.body.appendChild(overlay);

        var video = overlay.querySelector('video');
        var msg = overlay.querySelector('.scan-msg');
        var stream = null, timer = null, busy = false, closed = false;
        var last = '', lastAt = 0;

        function say(text) { msg.textContent = text; }

        function close() {
            if (closed) return;
            closed = true;
            clearInterval(timer);
            if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
            document.removeEventListener('keydown', onKey);
            overlay.remove();
            if (opts.onClose) opts.onClose();
        }

        function onKey(e) { if (e.key === 'Escape') close(); }
        document.addEventListener('keydown', onKey);
        overlay.querySelector('.scan-close').addEventListener('click', close);

        /* one place for every decoder: same-code de-duplication and the callbacks */
        function found(value) {
            if (closed || !value) return;
            var now = Date.now();
            if (value === last && now - lastAt < 2500) return;   // same barcode again: ignore for a moment
            last = value;
            lastAt = now;
            if (opts.onCode) opts.onCode(value);
            if (!opts.keepOpen) close();
            else say('Added: ' + value + '. Scan the next item.');
        }

        if (!global.isSecureContext) {
            say('The camera needs a secure connection (https). Type the code, or use a barcode scanner.');
            return { close: close };
        }
        if (!cameraSupported()) {
            say('This browser cannot use the camera here. Type the code, or use a barcode scanner.');
            return { close: close };
        }

        function startCamera() {
            return navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
                .then(function (s) {
                    if (closed) { s.getTracks().forEach(function (t) { t.stop(); }); return null; }
                    stream = s;
                    video.srcObject = s;
                    return video.play();
                });
        }

        function ready() {
            if (closed) return;
            say(opts.keepOpen ? 'Scan an item. It is added to the sale.' : 'Point the camera at the barcode.');
        }

        function cameraError(err) {
            var name = err && err.name ? err.name : 'error';
            say('Camera not available (' + name + '). Allow camera permission for MediGen, or type the code.');
        }

        if (nativeSupported()) {
            /* Chrome, Edge, Android: built-in detector, checked every 350 ms */
            var detector = new global.BarcodeDetector({ formats: FORMATS });
            startCamera().then(function () {
                if (closed) return;
                ready();
                timer = setInterval(function () {
                    if (closed || busy || video.readyState < 2) return;
                    busy = true;
                    detector.detect(video).then(function (codes) {
                        busy = false;
                        if (codes.length) found(codes[0].rawValue);
                    }).catch(function () { busy = false; });
                }, 350);
            }).catch(cameraError);
            return { close: close };
        }

        /* iPhone Safari, Firefox: ZXing reader (loaded once) reads frames from the same video */
        say('Starting camera...');
        startCamera().then(function () {
            if (closed) return null;
            return loadZxing();
        }).then(function (ZX) {
            if (!ZX || closed) return;
            var reader = new ZX.BrowserMultiFormatReader();
            ready();
            reader.decodeFromVideoElement(video, function (result) {
                if (result && !closed) found(result.getText());
            });
        }).catch(function (err) {
            if (closed) return;
            if (/zxing/.test((err && err.message) || '')) {
                say('Barcode reader could not load (check the internet connection). Type the code, or use a barcode scanner.');
            } else {
                cameraError(err);
            }
        });

        return { close: close };
    }

    // Scan into the input that sits next to the button (used on the medicine form).
    function fillFrom(button) {
        var field = button.closest('.scan-field');
        var input = field ? field.querySelector('input') : null;
        if (!input) return;
        open({
            onCode: function (value) {
                input.value = value;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
    }

    global.MediScan = { open: open, fillFrom: fillFrom, supported: barcodeSupported, nativeSupported: nativeSupported };
})(window);
