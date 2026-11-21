# MediGen AI Pro — v97.00 Changelog

Theme file: v97-theme.css (Nexus look waisa hi). v96.00 ki tamam features barqarar
(Daily Digest, receipt Back buttons, backup status sab shamil).

## 1. Refill Reminders (naya page /refills)
- Jin customers ne wahi dawai kam az kam 2 dafa li hai, unke kharidari ke asal
  waqfay (average gap) se program andaaza lagata hai ke agli dawai kab due hai.
- List: customer, dawai, aakhri kharid, waqfa, due date (badge: "5 din baqi" /
  "Aaj due" / "X din guzar gaye"). Due window: 10 din pehle se 14 din baad tak.
- Har customer ke liye ek-click WhatsApp Reminder (uske number par).
- Daily Digest par bhi refill strip ata hai jab koi due ho.
- Ye andaaza unke apne pattern par hai — koi medical hidayat nahi.

## 2. Expiry Clearance (naya page /expiry-clearance)
- 90 din ke andar (aur 30 din tak ke expired) batches ki amal list: kitne din
  baqi, qty, rate, aur phansi hui kul rakam (sale rate par).
- Har batch ke samne tajweez: <=30 din 15% off, 31-60 din 10%, 61-90 din 5%
  (sirf tajweez — program rate khud NAHI badalta), expired par "sale rokein,
  supplier return" ki hidayat. Print button mojood.

## 3. Backup Restore Test (Settings -> Security)
- Naya button "Test backup restore": aakhri backup ko alag throwaway database
  (medigen_restore_test) me restore karke medicines/customers/sales gin kar
  asal verdict deta hai, phir test database delete kar deta hai.
- Asal database ko haath nahi lagta. Script: scripts/restore_test.py.
- Live tasdeeq: "RESTORE TEST OK — medicines=5 customers=3 sales=6" aur Settings
  ke andar button se bhi PASS flash aya.

## Tasdeeq
- test_v97_pro.py: 100 checks passed, 0 failed.
- Poora suite: mock 2424 passed / 0 failed; live MySQL 2479 passed / 0 failed.
- Teeno features asal data ke sath browser screenshots me dekhe gaye (refill:
  Hasnain/Ibuprofen "5 din baqi"; clearance: Panadol batch Rs 4,000 at risk;
  restore test PASS flash).
- Windows .bat files asal Windows PC par unverified hain (hamesha ki tarah).
