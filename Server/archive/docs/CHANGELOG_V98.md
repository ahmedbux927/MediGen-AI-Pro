# MediGen AI Pro — v98.00 Changelog (Security & Final Wrap)

Theme file: v98-theme.css (Nexus look waisa hi). v97 ki tamam features barqarar.

## Security audit (jo pehle se mazboot tha — tasdeeq ki gayi)
- Passwords bcrypt-hashed; login par brute-force lock (galat koshishon par kuch
  minute band, database me record — restart se reset nahi hota).
- Har POST form par CSRF token khud-kar; session cookie HttpOnly + SameSite=Lax.
- Security headers har jawab par: X-Frame-Options, nosniff, Referrer-Policy,
  Permissions-Policy, Cache-Control no-store.
- Profile photo upload: extension whitelist + 2 MB + asal image ki jaanch.
- User banana: username/full-name/role validation + password policy helper.
- Debug mode default band (FLASK_DEBUG=1 se hi khulta hai).

## v98 me tabdeeli
1. Customer Portal HATA diya: /portal ek public (baghair login) PIN wala
   darwaza tha jo counter wali dukaan istemal hi nahi karti — ghair-zaroori
   attack surface khatam. Routes, service, templates, Admin hub card — sab saaf.
   (Customers table ke portal PIN columns waise hi chor diye — data ko haath
   lagana zaroori nahi tha.)
2. License banner ki fazool warning band: jab licensing is PC par set hi nahi
   (no_secret), to har page par narangi warning nahi ayegi. Asal license
   maslay (expired/invalid) par banner barqarar hai.
3. Naya LOGO: MediGen AI Pro ka apna logo (navy + teal cross/pulse/leaf) —
   login page (dono jagah), sidebar, browser favicon, PWA icons (192/512) aur
   APK icon — har jagah ek hi pehchan. Master file: MediGen_Logo.png.
4. ANDROID APK (MediGenAIPro.apk, package ke sath): phone par install karein,
   pehli dafa dukaan ke PC ka address (masalan http://192.168.1.100:5000)
   likhen — app yaad rakh legi aur program phone par khul jayega. Shartein:
   PC par program chala ho, phone usi Wi-Fi par ho. Address badalna ho to
   ghalat address par app khud setup screen le ayegi. APK debug key se signed
   hai — phone "is source se install allow karein" mang sakta hai.
   (Ye PC server ka saathi app hai; data PC par hi rehta hai.)

## Exception handling / user management — live audit
- Admin se 35 main routes crawl: koi 500 nahi, koi traceback nahi.
- Kharab inputs: /invoice/99999/thermal, /medicines/edit/abc, /invoice/abc —
  sab friendly jawab, koi crash nahi.
- Cashier test user: /settings, /users, /digest, /owner — sab par access
  denied (redirect); /sales/new aur /dashboard theek chaltay hain.
- AI Assistant offline: 3 sawalon (dawai ka istemal, software how-to, side
  effects) ke sahi jawab live parakhe. Online Gemini ke liye aapki apni API
  key chahiye (Settings -> AI Assistant -> Test connection asal verdict deta hai).

## Kya NAHI hataya (aur kyun)
- Controlled Register: narcotic dawaiyon ka qanuni record — hatana ghalat hota.
- Drip / Cold Chain / Branches / Rx Scan: ye roz ke pages (hubs, records) se
  juray hain; andha-dhund hatane se dukaan ka chalta kaam toot sakta tha.
  Ye chhotay aur mehfooz (login + role ke peechay) hain.

## Tasdeeq
- test_v98_pro.py: 110 checks passed, 0 failed.
- Poora suite: mock 2394 / 0 failed; live MySQL 2449 / 0 failed (portal ke
  ~30 tests usi ke sath gaye — tadaad is liye kam hai).
- APK: apksigner verify PASS. Windows .bat asal PC par unverified (hamesha ki tarah).
