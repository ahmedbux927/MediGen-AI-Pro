# MediGen v66 - Add medicine form no longer looks blocked

## Cause
- Category is required. A shop with no categories yet has only "Select Category" in the list.
- Clicking Save did nothing: the browser's validation bubble appeared inside the modal, often out of view, and no message was shown.

## Fix (templates/medicines.html only, backend unchanged)
- When there are no categories, the Add Medicine dialog shows a yellow note with a link to the Categories page.
- The form uses novalidate; our own check lists the missing fields in a red box inside the dialog, e.g. "Please fill: Category."
- The field that is missing gets focus.
- Save is still blocked until the required fields are filled, and the server still checks everything.

## Tested
- Playwright on a mock page: no category shows the note; Save shows "Please fill: Category." and sends nothing; with a category set the form is posted.
- tests/run_all.py: 1341 passed, 0 failed. Freeze manifest refreshed.

## Still to check on the shop PC
- Create a category first, then add a medicine with a barcode and opening stock.
- Look at logs\medigen.log if the server returns an error after Save.
