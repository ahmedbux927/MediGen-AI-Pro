# MediGen AI Pro — Pharmacy ERP aur Point of Sale

Version: `Config.APP_VERSION` (config.py) — har page par wahi version nazar aata hai.
Ye program aik hi dukaan ke Windows PC ke liye hai: sale (POS), stock aur batches,
purchases, udhaar, reports, backup — sab aik jagah. Data MySQL me rehta hai,
program Flask + waitress par chalta hai.

## Pehli dafa setup (sirf aik dafa)

1. Python 3 aur MySQL 8 install hon (MySQL service ka naam aam tor par `MySQL80`).
2. Is `Server` folder ko apni jagah rakhein (masalan Desktop par).
3. `.env` file banayein: `.env.example` ki copy kar ke `DB_PASSWORD` (apna MySQL
   password) aur `SECRET_KEY` set karein. **.env kabhi kisi ko na bhejen.**
4. Naya khali database ho to MySQL me pehle `database/schema.sql` phir
   `database/sample_data.sql` chalayen, phir `python create_admin.py` se admin banayein.
   Purana database ho to ye step nahi — program khud migrations laga deta hai.
5. `pip install -r requirements.txt` (internet ho to; vendor files pehle se mojood hain).

## Roz chalana

- **`START_MEDIGEN.bat`** double-click karein. Ye MySQL check karta hai, server
  chalata hai, ready hone par browser khud khul jata hai. Masla aye to ye ruk kar
  wajah batata hai (band nahi hota).
- Browser me address: `http://127.0.0.1:5000`
- Dukaan ke doosre PC / phone se: usi Wi-Fi par `http://<is PC ka IP>:5000`
  ya Android app (neeche dekhen).

## Zaroori kaam

- **Backup:** Settings → Security me "Backup now" button hai. Roz ka auto-backup
  chahiye to `scripts/schedule_daily_backup.bat` aik dafa Administrator se chalayen
  (roz 23:30). Backup kabhi purana ho jaye to Digest page par warning aati hai.
- **AI Assistant:** Settings → AI Assistant me apni Gemini key dalen aur
  "Test connection" dabayein. Key ke baghair bhi assistant dukaan ke sawalon ka
  jawab offline deta hai. Roz ka AI khulasa (Daily AI Summary) wahi se on hota hai.
- **Cash drawer:** pehle Cash page par drawer asal opening rakam se kholen;
  band drawer par Cash sale nahi hoti (ye hifazati rule hai).
- **Import:** bari list ke liye Medicines → "Import with preview" — pehle preview,
  phir Confirm, aur Undo bhi mumkin hai.
- **Barcode labels:** Medicines → Labels se shelf labels ki PDF print hoti hai.

## Android app

`android/` folder me WebView app hai (phone par dukaan ka program, sirf local
Wi-Fi par). Banane ka tareeqa: `android/BUILD_APK.md`. Phone par test ki list:
`android/TEST_CHECKLIST.md`. Tayyar APK package ke root me `MediGenAIPro.apk`
ke naam se milta hai (debug-signed — apni dukaan ke phone ke liye theek hai).

## Madad ke liye files

- `CHANGELOG.md` — version ki tabdeeliyan
- Package ke root me: `SHOP_TEST_CHECKLIST.md` (PC par khud test karne ki list),
  `QA_MATRIX.md` (kis user ko kya dikhta hai), `OPEN_DECISIONS.md` (malik ke
  faisle ke muntazir kaam), `PROGRESS.md` / `CHANGES.md` (is version ki tafseel).
