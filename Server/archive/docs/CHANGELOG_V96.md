# MediGen AI Pro — v96.00 Changelog

Theme file: v96-theme.css (Nexus look waisa hi — koi rang tabdeel nahi).
v95.00 ki tamam features barqarar.

## Naya: Daily Digest (sirf Admin)
- Naya page /digest (Owner Summary par button, aur Ctrl+K palette me "Daily Digest"):
  - Kal ki sale (bills + rakam) aur aaj ki sale ab tak
  - Low stock items (top 10) + kul tadaad
  - 90 din ke andar expire honay walay batches (top 10)
  - Customer udhaar: kul rakam, har customer ki baqi rakam, aur har customer ke liye
    ek-click WhatsApp Reminder button (uske number par, asal baqi rakam ke sath)
  - Backup ki haalat: aakhri backup kab bana, kitna bara, kul kitne backups
- Settings -> Shop me naya field "Owner WhatsApp": number save ho to Digest page par
  "WhatsApp par bhejen" button poora khulasa owner ko bhejta hai.

## Backup system (pehle se mojood, ab nazar bhi ata hai)
- Roz raat 11:30 khud-kar backup: scripts\backup_db.py + scripts\schedule_daily_backup.bat
  (ek dafa Administrator se chalana hai). Aakhri 30 backups mehfooz rehte hain.
- Dusri copy (USB / doosra folder): .env me OFFSITE_BACKUP_DIR set karein — har backup
  ki ek copy wahan bhi jati hai (pehle se mojood, ab Settings me hidayat bhi likhi hai).
- Settings -> Security ke Backup card me ab aakhri backup ki asal haalat dikhti hai;
  48 ghante se purana ho to surkh warning. Digest page par bhi backup warning ata hai.

## Fix: Receipt par Back button
- Thermal receipt par ab "Back — New Sale" aur "Dashboard" buttons hain (sirf screen
  par, print nahi hotay). Receipt ke baad wapas janay ke liye poori application band
  karne ki zaroorat khatam (user ki report par fix).

## Tasdeeq
- test_v96_pro.py: 89 checks passed, 0 failed (digest, backup status, receipt buttons).
- Poora mock suite aur live MySQL suite: delivery note me darj hatmi tadaad dekhen.
- Digest page asal data (kal ki sale, low stock, expiring batch, udhaar wala customer)
  ke sath browser me screenshot karke dekha gaya.
- Windows .bat files asal Windows PC par phir bhi unverified hain.
