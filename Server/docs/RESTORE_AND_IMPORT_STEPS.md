# Backup restore aur product import: step by step (v49)

Ye guide un files ke liye hai jo Workbench se export hui hain:
`Database backend backup` folder (ek table = ek .sql file) aur `MediGen_AI_Pro_230_Pharmacy_Products.docx`.

## 0. Pehle ye samajh lein

- **Backup mein asli logon ka data hai**: users (naam, username, email, phone, password hash), remember tokens, password reset codes.
  Ye folder **project zip mein na rakhein** aur kisi ko na bhejein. Alag, safe jagah par rakhein.
- **230 products ki list DEMO hai**: barcodes, prices, batches, expiry dates aur suppliers mock hain. Strength, manufacturer aur Rx flag
  mukammal nahi hain. Is list ko **asli shop database mein import na karein**, warna fake stock aur fake expiry bik sakti hai.
  Ye list sirf check database, training ya demo ke liye hai.
- Asal shop ke products ke liye supplier ki asli price list chahiye (Excel ya CSV).

## 1. Shuru karne se pehle

1. Old app band karein (server aur MediGenAIPro.exe).
2. Shop database ka **naya backup** lein (backup_db.bat ya Workbench export). Ye sab se pehli safety hai.
3. `.env` ki copy alag save karein.

## 2. Backup ko check database mein restore karein (live database ko nahi chhuna)

Command prompt mein project folder se:

```
python scripts\restore_backup.py "C:\path\to\Database backend backup" --prefix pharmacy_management_system
```

- Naya database banta hai: `pharmacy_restore_check`. Live database `pharmacy_management_system` **nahi badlega**.
- Script ko MySQL ka `mysql` command chahiye (MySQL 8 ka bin folder PATH mein ho).
- Agar `pharmacy_restore_check` pehle se hai, script ruk jaati hai. Pehle usay drop karein ya `--db` ka naam badlein.

Expected row counts (backup files ki ginti ke hisaab se; restore ke baad inhe milana zaroori hai):

| Table | Rows | Table | Rows |
|---|---|---|---|
| medicines | 19 | sales | 16 |
| batches | 23 | sale_items | 28 |
| categories | 62 | sale_payments | 10 |
| customers | 12 | stock_adjustments | 10 |
| suppliers | 6 | purchase_orders | 7 |
| purchase_items | 8 | prescriptions | 4 |
| prescription_items | 5 | sale_returns | 1 |
| audit_log | 173 | sale_return_items | 1 |
| users | 3 | roles | 3 |
| chat_history | 2 | login_attempts | 5 |

Agar koi number mukhtalif ho to import se pehle ruk jayein aur mujhe batayein.

## 3. Check database par app chalayein

1. `.env` mein `DB_NAME=pharmacy_restore_check` karein (sirf check ke liye).
2. App start karein. Startup par naye columns (generic name, manufacturer, strength, Rx flag, import source waghera) aur barcode unique index
   khud ban jaate hain. Agar barcode unique index na bane to log mein warning aayegi (purane data mein duplicate barcode ho sakte hain).
3. Login karein. Medicines page par 19 items hon.
4. Check ke baad sensitive data saaf karein (check database par):
   ```
   DELETE FROM remember_tokens;
   DELETE FROM password_resets;
   ```
   Admin password bhi check karke badlein.

## 4. Product list ka dry run (kuch nahi likha jaata)

Pehle Word file ko CSV mein badlein (ye pehle se ho chuki hai: `database\samples\pharmacy_products_230_demo.csv`):

```
python scripts\docx_products_to_csv.py database\samples\MediGen_AI_Pro_230_Pharmacy_Products.docx
python scripts\import_products.py database\samples\pharmacy_products_230_demo.csv
```

Expected result (check database par):
- create 227, skip 3 (Panadol, Panadol Extra, Disprin: ye pehle se hain, inhe chhoda jata hai), error 0.
- Report file `pharmacy_products_230_demo_import_report.csv` banti hai, har row ka action aur warning ke saath.

Dry run se kuch nahi likha jata. Agar errors hon to pehle unhe theek karein. Ek bhi error ho to koi row nahi likhi jaati.

## 5. Import likhna (sirf check database par)

```
python scripts\import_products.py database\samples\pharmacy_products_230_demo.csv --commit
```

- Sab ya kuch nahi: agar koi row invalid ho to poori import rok di jaati hai.
- Har nayi medicine ke liye ek audit entry banti hai (`medicine.import`).
- Naya stock ek batch ki shakl mein banta hai (expiry ke saath), taake FEFO kaam kare.
- Existing items ka stock kabhi nahi badalta.
- Existing items ki price/details badalne ke liye `--update-existing` lagayein (dry run pehle).

## 6. Asli shop database par (jab check theek ho aur supplier ki asli list ho)

1. Shop database ka backup lein.
2. Supplier ki asli list (CSV ya XLSX) par dry run karein:
   `python scripts\import_products.py FILE.xlsx`
3. Report check karein: `missing` ginti (strength, manufacturer, Rx) aur warnings (cost > price, expiry 30 din mein).
4. Theek ho to `--commit` chalayein.
5. Rx flag wali NULL rows pharmacist confirm karein. Import Rx ko kabhi "No" nahi karta.

## 7. Kuch ghalat ho jaye

- Import ke baad galat data ho to backup se restore karein (pehle backup lazmi lein).
- Import wali medicines is tag se milti hain: `import_source` column (demo list ke liye `MediGen_AI_Pro_230_Pharmacy_Products` ya CSV ka naam).
- Jin medicines par sale ho chuki hai unhe delete na karein (sales ka record kharab hoga). Ghalat data ko stock adjustment ya price edit se theek karein.

## 8. Test chalana

```
python tests\run_all.py
```

Expected: TOTAL 1130 passed, 0 failed. Live MySQL test (`--live`) shop PC par alag se chalayein.
