# MediGen AI Pro - Video tutorial scripts

Six short videos, 2 to 4 minutes each. Record at 1080p, with the sidebar visible. Use demo data (`database/sample_data.sql`). Never show real customer names or phone numbers.

## Video 1 - Install and first login (3 min)
- **Scene 1 (0:00):** Run the MediGen installer. Show Next, Next, Install. Mention Python 3.10+ and MySQL are needed first.
- **Scene 2 (0:45):** Open `.env`. Show DB_HOST, DB_USER, DB_PASSWORD, DB_NAME.
- **Scene 3 (1:30):** Run `python create_admin.py`. Create the admin.
- **Scene 4 (2:15):** Start the app from the desktop shortcut. Log in. Show the Dashboard.
- **Narration cue:** "Only the admin account needs to be made by hand. Everything else is inside the app."

## Video 2 - Adding medicines and stock (3 min)
- **Scene 1:** Medicines > Add. Fill name, category, price, cost, reorder level.
- **Scene 2:** Enter opening stock. Show that history is written.
- **Scene 3:** Adjust > In, reason "Found". Then Out, reason "Damaged". Show the error when Out is above the stock.
- **Scene 4:** Show the history popup and the back arrow.

## Video 3 - Batches and expiry (3 min)
- **Scene 1:** Purchases > New Purchase with batch number and a future expiry date.
- **Scene 2:** Batches & Expiry. Explain the status: Expired, Soon, OK, Empty.
- **Scene 3:** Write off an expired batch. Show the history line.
- **Scene 4:** Alerts page. Show low stock and expiring items.

## Video 4 - Making a sale (4 min)
- **Scene 1:** New Sale. Add two medicines. Show the live total.
- **Scene 2:** Add a 10% discount. Show the total change.
- **Scene 3:** Partial payment with a customer. Show the balance going to Customer Dues.
- **Scene 4:** Print the 80 mm receipt.
- **Scene 5:** Return one item. Show the refund.

## Video 5 - Prescriptions and allergy warnings (3 min)
- **Scene 1:** Prescriptions > New. Choose a customer whose history mentions an allergy.
- **Scene 2:** Add an antibiotic. Show the allergy warning on save.
- **Scene 3:** Open the prescription and load it into a new sale.

## Video 6 - Reports, backups and users (4 min)
- **Scene 1:** Reports. Use the Today / 7 days / 30 days presets.
- **Scene 2:** Export the Sales tab to Excel and PDF. Show the Tax summary with its "confirm with your tax advisor" note.
- **Scene 3:** Run `scripts\backup_db.bat`. Show the new file in `backups`.
- **Scene 4:** Users > Add a Cashier. Show the role limits.

## Recording checklist
- Use demo data only. Hide the browser address bar if it shows the PC IP.
- Turn off notifications. Set the browser zoom to 100%.
- Subtitles in English. Roman Urdu voice-over is optional.
