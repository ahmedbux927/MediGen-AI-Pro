# MediGen v69 - Browser cache refresh (fixes "same error still shows" after an update)

## Why
- The service worker (static/js/sw.js) keeps static files (CSS, JS) in the browser and serves them first.
  An older browser copy of pages.css and app.js kept the popup bug from the old version.
- Some links had no version number, so the browser kept the old file.

## Changes
- sw.js cache name medigen-static-v2 -> medigen-static-v3 (the browser deletes the old cache when it starts the new version).
- Version numbers raised for changed files: pages.css ?v=39, app.js ?v=23, shell-light.css ?v=2, assistant.css and assistant.js ?v=3, charts.js ?v=25, login.css ?v=2.

## Shop PC steps after extracting v69
1. Close all browser windows that show the app.
2. Stop the server and start it again (python app.py or the start script).
3. Open the app and press Ctrl+F5 (hard refresh).
4. If the popup still looks wrong: in Chrome or Edge press F12 > Application > Service workers > Unregister, then Storage > Clear site data, then refresh.

## Tests
- tests/run_all.py: 1341 passed, 0 failed. Freeze manifest refreshed.
