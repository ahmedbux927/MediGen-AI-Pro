# MediGen v68 - Popups (Add Medicine, Add Customer, etc.) show on top, with the page dimmed behind

## Cause (found with the browser, not guessed)
- The page wrapper (main.main-content) had a fade-in animation that kept running its "both" fill after it ended.
  That made the wrapper a stacking layer, so the popup sat under the dark page overlay. The whole screen looked dimmed,
  including the popup, which is what the shop PC showed.
- Popups taller than the window had their footer (Cancel / Save) below the screen.

## Fix
- pages.css: the fade uses "backwards" fill, so nothing stays on after the animation ends.
- app.js: every popup is moved to the end of <body> once, so the page overlay always sits below it.
- shell-light.css: popup body scrolls inside the window; header and buttons stay visible.
- v67 validation message still works (Please fill: Full Name.).

## Tested (Playwright, real Bootstrap, 1354x603 like the shop screenshot)
- Element at the popup centre is now the popup, not the overlay. Screenshot shows the popup bright with Cancel and Save visible.
- Add Customer: empty name -> message in the popup, no POST, message hides on typing.
- tests/run_all.py: 1341 passed, 0 failed. Freeze manifest refreshed.

## Shop PC check
- Open Add Medicine and Add Customer on a short window. The popup should be bright, on top, and its Save button reachable.
