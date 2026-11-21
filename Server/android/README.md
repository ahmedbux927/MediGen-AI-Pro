# MediGen AI Pro - Android app (source)

WebView companion app (package com.medigen.aipro). First run asks for the shop
PC address (for example http://192.168.1.100:5000) and remembers it; if the
server cannot be reached, the setup screen returns so the address can be fixed.
The phone must be on the same Wi-Fi as the shop PC, and MediGen must be running
on the PC. The ready-to-install APK (MediGenAIPro.apk) is in the package root.
Full native upgrade (token login, biometric lock, native barcode scan) is
STAGE 4 of the master plan - see OPEN_ITEMS.md. Build steps: BUILD_APK.md (Stage 4).
