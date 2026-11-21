# Build the Windows program (.exe) and the phone app (APK)

## A. Windows program (MediGenAIPro.exe) - on the PC
1. Keep the project folder with `static\vendor` (the offline files) in it.
2. Open the project folder, then run:  `build_exe.bat`
3. Wait for "Done". The program is in `dist\MediGenAIPro\`.
4. Check `dist\MediGenAIPro\.env`: set `DB_PASSWORD` to the MySQL password.
5. Start `dist\MediGenAIPro\MediGenAIPro.exe`. It opens MediGen in the browser. Keep its black window open while you work.

Notes:
- MySQL 8.0 must be installed and running. The program does not include MySQL.
- Keep the whole `dist\MediGenAIPro` folder together. Do not move the exe alone.
- The first build can take several minutes.
- Windows SmartScreen may warn "Unknown publisher". Choose "More info > Run anyway". A signed certificate removes this warning (costs money).
- Optional installer: `installer\MediGen.iss` (Inno Setup 6) builds a Setup file. It needs Python on the PC.

## B. Phone app (APK) - in Android Studio
1. Install Android Studio (free). Open the `android` folder and let it sync.
2. Menu: Build > Build Bundle(s) / APK(s) > Build APK(s).
3. The file is `android\app\build\outputs\apk\debug\app-debug.apk`. Copy it to the phone and install it.
4. First open: enter the PC address (for example `http://192.168.1.10:5000`). The phone must be on the same WiFi as the PC, and the PC must be running MediGen.

Important about the APK: it shows MediGen running on the PC. It is not a separate offline app. If the PC is off, the phone app cannot load data.

## C. What is still needed from you
- Run build_exe.bat on the PC, and tell me any error it prints.
- Build the APK in Android Studio, and tell me any error it prints.
- I cannot build the .exe or the APK in this environment. These need Windows and Android Studio.
