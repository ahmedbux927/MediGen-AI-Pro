# MediGen v75 - Camera barcode scan on every phone browser (includes v72-v74)

## What changed
- The camera scanner (POS "Camera" button and the medicine form "Scan" button) now works on browsers that had no barcode reader:
  - Chrome, Edge, Android: built-in `BarcodeDetector` (as before).
  - iPhone Safari, Firefox: the ZXing barcode reader is loaded once from jsdelivr (`@zxing/library@0.21.3`) and reads the same camera feed.
- If the reader cannot load (no internet), the scanner says so and suggests typing the code.
- If the camera is blocked, the message shows the reason (e.g. NotAllowedError).
- Public API is unchanged: `MediScan.open`, `MediScan.fillFrom`, `MediScan.supported`.

## Files
- `static/js/scanner.js` rewritten (v32). `templates/base.html` loads `?v=32`.
- `static/js/sw.js`: cache name bumped to `medigen-static-v4` so phones fetch the new file.
- `tests/test_scanner_fallback.py` (new, 11 source checks).
- Browser check (headless Chromium): permission-denied message and no-camera message both show, no page errors.

## Tests
- `tests/run_all.py` passes (see the last run). Freeze manifest regenerated.

## Limits
- Needs https (or 127.0.0.1) for the camera. Plain http on a LAN IP is blocked by browsers.
- Not tested on a real iPhone or Android phone in this sandbox. Please test on the phone before relying on it.
- The ZXing file comes from jsdelivr. If the shop's internet blocks jsdelivr, the fallback shows a message and the code can still be typed or scanned with a USB scanner.

## Check on the phone
1. Open the app over https (or the PC address you use) on the phone.
2. New Sale → Camera → point at a medicine barcode. The item should be added (keep-open mode).
3. Medicine add form → Scan → the barcode fills the field.
