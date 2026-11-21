# OPEN_DECISIONS — malik (owner) ke faisle ke muntazir

Ye cheezen jaan boojh kar NAHI banayi gayin (Master Prompt v4, Section P).
Har aik ke liye hook ya jagah program me mojood hai; faisla malik ka hai.

1. **B2 — "No stock" ginti milan (stock reconciliation):** tool tab banega jab
   malik dukaan ke database par `Server/database/diagnostics/stock_mismatch_report.sql`
   chala kar us ki output bhejen. Us ke baghair andaza lagana ghalat hoga.
   POS ki stock ki asal tareef program me ye hai: min(stock_quantity, fresh batches).
2. **H / G schedule dawaiyon ke rules:** pharmacist ko aik table bharni hai
   (konsi dawai kis schedule me aati hai) — us ke baghair rules nahi lag sakte.
3. **Licensed drug-interaction database:** abhi warning-pairs wala chhota tool
   hai jo saaf "placeholder" likha hua hai. Asal licensed data khareedna malik ka faisla hai.
4. **Prescription ki photo Gemini ko bhejna:** privacy ka faisla. Abhi photo
   sirf PC par Tesseract se parhi jati hai; Gemini ko mareez ki koi maloomat
   (naam, phone, address, prescription image) nahi jati.
5. **FBR integration:** NTN aur FBR ki API maloomat chahiye — malik faraham karein to banega.
6. **Internet hosting / HTTPS / cloud MySQL / phone par offline database:**
   abhi program LAN ke liye hai. Bahar se access chahiye to ye alag faisla hai.
7. **Online store, rider app, online payments (JazzCash/Easypaisa dukaan par
   mojood hain; online checkout nahi):** alag project ke tor par faisla hoga.
8. **Smart substitute (licensed data par):** licensed data ke baghair nahi.
9. **AI_ENABLED default:** program me assistant default ON hai (key ho to online,
   na ho to offline). Master Prompt ki aik line OFF kehti thi; malik ki pehli
   hidayat (Gemini assistant chahiye) ko tarjeeh di gayi. Badalna ho to bataein.
10. **Desktop (.exe) packaging:** desktop.py mojood hai; archive sirf malik ki
    ijazat se hoga (abhi nahi kiya).
11. **Key rotation:** jo API key kabhi file ya chat me aayi ho, use badalna
    malik ka apna kaam hai (Settings → AI Assistant me nayi key dalen).
12. **Brand naam / logo ka hatmi faisla:** mojooda logo (v98) chal raha hai.
13. **Dukaan ke PC aur phone par test:** `SHOP_TEST_CHECKLIST.md` malik khud
    chalayen — agent ne Windows PC aur asal phone par test NAHI kiya.
