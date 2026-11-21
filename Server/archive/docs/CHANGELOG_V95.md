# MediGen AI Pro — v95.00 Changelog

Owner ke bheje hue "MediGen Nexus — Premium Light UI Concept" ke 62 design
screenshots ke mutabiq pura frontend usi andaaz me rang diya gaya hai.
Note: wo screenshots design mockups thay (unke apne README ke mutabiq sample
data ke sath) — yahan sirf DESIGN (rang, cards, layout ka andaaz) asal chalte
hue system par lagaya gaya hai; andar apka asal data hi nazar ayega.

## Nexus design jo lagaya gaya
- **Sidebar: gehri navy rail** (#0a1a2f → #0d2138), teal logo nishan, user card
  halki navy parhal, section headings chhote bareek haroof me, active item par
  teal ki parhal (pill) — bilkul mockup jaisi. Dono modes me yahi rail.
- **Halka canvas:** page ka pas-e-manzar halka neela-grey (#edf1f6); cards
  safed, bareek kinara (#e2e8f0), naram saaya — tez rang khatam.
- **Top bar safed** saaf, kinare ke sath; andar ke tamam chips safed gol
  kinaron wale.
- **Headings gehray navy** (#10243c), numbers bare aur gehray, label chhote
  bareek haroof (small caps) me jahan mumkin.
- **Teal action rang:** primary buttons, POS ki bill wali patti (navy → teal),
  item badges, table ke headers halke grey par small caps.
- **Login hamesha halki:** Nexus jaisi halki professional — safed card, navy
  heading, safed fields, teal Sign In. (Is se pehle dark profile save ho to
  login par heading ghayeb ho jati thi — wo purani khami bhi isi me theek ho
  gayi.)
- **Chatbot** ke neelay/jaamni rang navy → teal me badle gaye taake pura
  system ek hi pehchan lage.

## Dark mode
- Dark mode bhi theek rakha gaya hai: navy sidebar, gehray cards, top bar
  gehri — aur is dafa har button ki likhai dark mode me saaf parhi jati hai
  (ek pichhli khami: dark mode me do buttons ki likhai ghayeb thi, fix ho gayi).
- Welcome wali patti pehle ki tarah halki hi hai (owner ki hidayat par).

## Jo nahi badla
- Tamam v94 features mehfooz: JazzCash/Easypaisa, WhatsApp share, QR code,
  success tick, asal backup button, Ctrl+K palette, Import_Lists.
- Backend, database aur tamam hisaab-kitab bilkul waisa hi hai.

## Tasdeeq (live, asal MySQL + browser)
- Dashboard, POS, Medicines, Login ke screenshots dono modes me saaf —
  Nexus mockup se mila kar dekhe gaye.
- Test suites: mock 2403/0, full incl. live MySQL **2458 passed / 0 failed**.

## Ab bhi tasdeeq talab
- Windows .bat scripts asal Windows PC par (har version ki tarah).
- Gemini ka asal jawab apki apni API key se apke PC par.

## Install
Purana tareeqa: pehle purane Server folder se `.env`, `backups` aur
`static/profiles` mehfooz karen, phir PURA Server folder naye se replace
karen, mehfooz cheezein wapas rakhen, aur START_DESKTOP.bat chalayen.
