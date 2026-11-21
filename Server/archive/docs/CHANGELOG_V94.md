# MediGen AI Pro — v94.00 Changelog

Owner ki final pasand par banaya gaya: Ivory + Bronze sidebar, halki welcome
patti, aur "Digital Empire" brief ke woh hisse jo asal me kaam karte hain.

## Look
- **Sidebar: Ivory + Bronze** — garam ivory (cream) rail, bronze brand icon aur
  active accents, safed active pill. Dono modes me yahi rehti hai. (Is se pehle
  green, tez blue aur black/graphite owner ko pasand nahi aye thay.)
- **Welcome banner halki** — "Good morning/afternoon" wali patti ab light mode
  me kaali nahi; halki saaf patti hai, jaisi pehle thi.
- **Kinetic button press** — buttons dabne par halki spring jaisi feel
  (scale .96, spring curve).

## Nai asal features
- **JazzCash / Easypaisa** payment options New Sale aur Receive Payment dono
  jagah. Cash drawer ki pabandi sirf Cash par rehti hai; wallets Online ki
  tarah chalte hain. Daily closing me alag line ayegi.
  - Bug jo isi doran mila aur fix hua: purane databases me
    `sales.payment_method` ek ENUM tha (sirf Cash/Card/Online), is liye wallet
    sale save hi nahi hoti thi (error 1265). Ab app start hone par ENUM khud
    widen ho jata hai — purani values mehfooz, kuch rename/delete nahi hota.
    Fresh installs ke schema me bhi shamil hai.
- **WhatsApp share** — thermal receipt aur full invoice dono par "Share on
  WhatsApp" button: bill ka khulasa (shop, invoice #, total, payment method)
  pehle se likha hua khulta hai. Customer ka number bill par ho to seedha usi
  number par jata hai.
- **QR code** — dono invoices par bill summary ka QR (offline library bundled
  hai, internet nahi chahiye). Thermal receipt par print bhi hota hai.
- **Success tick** — sale mukammal hone par thermal page par animated green
  tick + "Sale completed" (sirf screen par, print me nahi ata).
- **Backup button (asal)** — Settings → Security → "Take backup now": wohi
  asal mysqldump backup chalata hai jo script chalata hai, aur sach batata
  hai — file ka naam success par, asal wajah failure par. Kuch bhi cloud par
  upload NAHI hota; backup isi PC ke Server\backups folder me banta hai.

## Jo brief me tha lekin jaan-bujh kar NAHI banaya
- Fake "cloud backup" ka success message, Face ID / biometric ka nakli UI,
  aur UPI (ye India ka system hai, Pakistan me nahi chalta). Ye cheezein
  dikhawa hotin, kaam nahi kartin — is liye nahi banayi.
- React/Next.js par pura rewrite nahi kiya: apka maujooda Flask system asal
  database ke sath chal raha hai; rewrite matlab mahino ka kaam aur chalti
  dukaan ka risk.

## Pehle se maujud (brief me dobara mange gaye thay)
- Offline mode + auto-sync (offline POS sync), PWA, thermal printing,
  remember-me, animation & sound toggles, chatbot mic, dashboard ke
  rolling/count-up numbers.

## Tasdeeq (live, asal MySQL + browser)
- JazzCash sale → invoice #1 thermal: "Paid (JazzCash) 100.00", QR print,
  WhatsApp link me sahi total/method.
- Settings se asal backup: `medigen_20261120_1437.sql` (62 KB) backups folder me.
- Dashboard light + dark screenshots saaf (ivory sidebar, halki banner).
- Test suites: mock 2402/0, full incl. live MySQL **2457 passed / 0 failed**.

## Ab bhi tasdeeq talab
- Windows .bat scripts asal Windows PC par (har version ki tarah).
- Gemini ka asal jawab apki apni API key se apke PC par (Settings → AI
  Assistant → Test connection wahan fori verdict dega).

## Install
Purana tareeqa: pehle purane Server folder se `.env`, `backups` aur
`static/profiles` mehfooz karen, phir PURA Server folder naye se replace
karen, mehfooz cheezein wapas rakhen, aur START_DESKTOP.bat chalayen.
File-by-file replace na karen. Pehli dafa start hone par payment ENUM khud
update ho jayega — apko kuch nahi karna.
