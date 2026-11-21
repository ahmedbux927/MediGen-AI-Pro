# SHOP TEST CHECKLIST — dukaan ke PC par khud test karein

Ye list malik apne Windows PC par chalayen. Agent ne ye test Windows PC par
NAHI kiye (wahan ka mahol mukhtalif hai: asal MySQL service, asal printer,
asal Gemini key, asal phone). Har line ke baad tick karein; jo fail ho us ki
screenshot aur waqt note kar ke bhejen.

## Lagana (install)
- [ ] Purani Server folder ka `.env`, `backups/` folder aur `static/profiles/`
      ki photos mehfooz jagah copy ki.
- [ ] Purani Server folder delete kar ke nayi Server folder rakhi (files
      mila kar copy NAHI kiye).
- [ ] Mehfooz `.env`, `backups/` aur photos wapas rakhen.
- [ ] `START_MEDIGEN.bat` chalaya — browser khud khula, login page aya.

## Pehle din ke test
- [ ] Admin login hota hai; ghalat password par saaf message aata hai.
- [ ] Dashboard par aaj ki sale, cash in hand (drawer ki opening ke saath) theek hai.
- [ ] Cash page: drawer band kar ke asal gin kar dobara khola.
- [ ] Aik Cash sale: Panadol becha → invoice bana → thermal print theek aya.
- [ ] Aik JazzCash/Easypaisa sale bhi ho gayi.
- [ ] Invoice par QR aur WhatsApp share kaam karte hain.
- [ ] Medicines page light aur dark dono modes me saaf parha jata hai
      (Settings se nahi, upar wale button se mode badal kar dekhen).
- [ ] Settings → AI Assistant: apni Gemini key dali, **Test connection**
      par "Connected" aya; phir AI Assistant se aik sawal pooch kar jawab mila.
- [ ] Settings → Security: **Backup now** chalaya; backup ki file aur size nazar aya.
- [ ] Settings → Security: **Restore test** chalaya — PASS aya.
- [ ] Data Quality: jin items ki price 0 hai, un ki price set ki.
- [ ] `scripts/schedule_daily_backup.bat` aik dafa Administrator se chalaya
      (roz ka auto-backup lag gaya).
- [ ] Users: cashier ke liye alag user banaya (admin sab share na karein).

## Phone (Android)
- [ ] `MediGenAIPro.apk` phone par install hua (pehle se ho to pehle uninstall
      karein — is dafa key wahi purani debug key hai, update bhi chalega).
- [ ] `android/TEST_CHECKLIST.md` ki tamam lines check ki (address, login
      yaad rehna, back button, camera scan, sale mukammal).
