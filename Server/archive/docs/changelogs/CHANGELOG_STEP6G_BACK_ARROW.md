# MediGen AI Pro - Step 6G: Flat sidebar and back arrow on every page

## Changed
- Sidebar: no "Menu" button. All pages are in one list (Dashboard, Medicines, Batches & Expiry, Categories, Customers, Suppliers, Sales, New Sale, Purchases, Prescriptions, Daily Closing, Customer Dues, Reports, Users, Records Clear, AI Assistant, Settings, My Profile). The list scrolls if needed.
- Red Logout button stays pinned at the bottom of the sidebar.
- Back arrow (round button, top left of the page header) on every page. It goes to the previous page, or to the Dashboard if there is no previous page.

## Test
- Full suite: 481 passed, 0 failed.
- Sandbox screenshot: flat list, Logout at the bottom, back button in the header. Icons are blank only in the sandbox (no internet for Bootstrap Icons).

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.
