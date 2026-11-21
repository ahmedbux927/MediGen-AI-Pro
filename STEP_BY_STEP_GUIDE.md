# MediGen AI Pro v101.03 — Step by Step Guide

## Hissa 1: Program install karna (dukaan ka PC)

1. Is package ki zip kholein. Andar `Server` folder, `MediGenAIPro.apk` aur ye guide hai.
2. Apni purani `Server` folder se pehle ye 3 cheezen alag mehfooz copy karein:
   - `.env` file (aap ki settings aur password)
   - `backups` folder
   - `static\profiles` folder (staff ki photos)
3. Purani `Server` folder **delete** karein. (Files mila kar copy na karein — is se purani kharabiyan wapas aa jati hain.)
4. Nayi `Server` folder wahan rakhein jahan purani thi.
5. Mehfooz ki hui `.env`, `backups` aur `profiles` wapas un ki jagah par rakhein.
6. `START_MEDIGEN.bat` double-click karein. Browser khud khul jayega — login karein.
7. Naya icon login page aur sidebar par nazar ayega. Agar purana dikhe to browser me **Ctrl + F5** dabain.

## Hissa 2: Windows application (Setup file) banana

Zaroorat: is PC par **Python 3** (pehle se hai) aur **Inno Setup 6** (aap ne install kar liya hai).

1. `Server` folder kholein.
2. **`MAKE_WINDOWS_APP.bat`** double-click karein.
3. Pehla step `MediGenAIPro.exe` banayega (kuch minute lagenge, internet chahiye pehli dafa).
4. Dusra step khud Inno Setup chala kar **`dist\MediGen_Setup_101.03.exe`** banayega.
5. Ye aik file hi poori application hai — backend samet. Isay kisi bhi Windows PC par chalayein:
   - Us PC par Python **nahi** chahiye.
   - MySQL 8 wahan pehle se ho, ya portable MySQL wala tareeqa `installer\README.md` me hai.
   - Pehli dafa Windows SmartScreen "Unknown publisher" dikha sakta hai — **More info → Run anyway** dabain (program code-signed nahi hai, ye aam baat hai).

## Hissa 3: Phone app (APK)

1. `MediGenAIPro.apk` phone par bhejein (WhatsApp / USB) aur install karein — purani app ke upar update ho jayegi, naya icon aa jayega.
2. Pehli dafa app dukaan ke PC ka address mangegi: wohi PC ka Wi-Fi wala address likhein, misal `192.168.1.10` (bina http ke bhi chalega). Phone aur PC aik hi Wi-Fi par hon.

## Hissa 4: Is version me naya kya hai

- **Naya icon** — Canva se bana hua professional icon (navy + teal cross/pulse/leaf) har jagah: Windows, Android, login, sidebar.
- **User delete theek ho gaya** — Users page par trash button ab aik dialog kholta hai:
  - Aam delete: jis user ki sales/records hain woh sirf **band (OFF)** hota hai, kuch nahi khota.
  - **"Delete permanently"** tick karke Delete dabain to account khatm ho jata hai aur us ki sales/records **'Deleted user'** ke naam par chale jate hain — dukaan ki history poori rehti hai.
  - Aakhri active Admin delete nahi ho sakta (dukaan lock hone se bachane ke liye).
- **Poora check** — login se aakhri page tak har route error-handling ke peeche hai; koi khamosh error nahi; dark/light/system teeno theme check hue; 2509 tests passed.

## Masla aye to

- Program khulte hi band ho jaye: `logs` folder ki aakhri file ka screenshot bhej dein.
- Setup file banne me error aye: black window ka screenshot bhej dein — jo pehli error hogi, wahi asal wajah hai.
