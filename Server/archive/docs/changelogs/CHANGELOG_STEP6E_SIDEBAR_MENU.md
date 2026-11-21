# MediGen AI Pro - Step 6E: Sidebar Menu slide and red Logout

## Changed
- Sidebar first view: Dashboard, a "Menu" button, and a red Logout button.
- "Menu" slides in the full list from Medicines down to My Profile (Medicines, Batches & Expiry, Categories, Customers, Suppliers, Transactions, Admin, AI Assistant, Settings, My Profile).
- Small back arrow at the top of the Menu panel slides back to the first view.
- Logout is a solid red button under the Menu button (it was hard to see before, because the CSS targeted a link, not the button).
- Role rules are unchanged: Suppliers, Purchases, Prescriptions, Admin section and Settings still show only for the roles that could see them before.

## Files
- templates/base.html (sidebar markup and a small script for the Menu / back buttons), pages.css v27.

## Test
- Full suite: 481 passed, 0 failed.
- Screenshot check in the sandbox: root view and Menu view both render. Bootstrap icons do not load in the sandbox, so icons may show as blank boxes there. They load on your PC.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5.
