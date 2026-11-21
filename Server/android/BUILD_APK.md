# Building the MediGen AI Pro Android app

The app is a small WebView companion: it opens the shop PC's MediGen server
on the phone (same Wi-Fi). It holds no database and works only while the PC
program is running.

## Option A — Android Studio / Gradle (normal way)

1. Install Android Studio (it brings the Android SDK and a JDK).
2. Open this `android/` folder as a project.
3. Let it sync (AGP 8.5.2, Gradle 8.7 — versions are pinned in
   `build.gradle` and `gradle/wrapper/gradle-wrapper.properties`).
4. Run → the app installs on a connected phone, or Build → Build APK(s)
   for a debug APK at `app/build/outputs/apk/debug/app-debug.apk`.

Note: AGP 8 wants the package name from `namespace` in `app/build.gradle`
(already set). If Android Studio complains about the `package` attribute in
`AndroidManifest.xml`, remove that one attribute — the namespace replaces it
(the manual build below uses the attribute, which is why it is still there).

## Option B — Manual pipeline (no Android Studio; this is how the shipped APK was built)

Needs a JDK 17 and the Android platform + build-tools zips. The steps:

1. `javac -encoding UTF-8 -cp android.jar -d classes app/src/com/medigen/aipro/*.java`
2. Generate `R.java` and package resources with `aapt` (manifest + `res/`).
3. Convert classes to DEX with `d8`.
4. Assemble the APK with `aapt`, then `zipalign`.
5. Sign (see below) and verify with `apksigner verify --print-certs`.

## Signed release build (owner does this once)

Debug-signed APKs work for the shop's own phones, but a release key is
better (updates keep working only with the same key).

1. Create the key ONCE and keep the file safe (password in the password
   manager, a copy on a USB stick). **Never commit the keystore or its
   password to the project folder or any zip.**
   `keytool -genkeypair -keystore medigen-release.jks -alias medigen -keyalg RSA -keysize 2048 -validity 10000`
2. Gradle: reference the keystore from `~/.gradle/gradle.properties`
   (outside the project) or use Android Studio's "Generate Signed Bundle/APK"
   wizard, which keeps the details out of the repo.
3. Manual pipeline: `apksigner sign --ks medigen-release.jks --out MediGenAIPro.apk unsigned.apk`.

## Version numbers

`versionCode` / `versionName` live in `app/build.gradle` **and**
`app/AndroidManifest.xml` (the manual build reads the manifest). Both must
match `APP_VERSION` in `Server/config.py` whenever a package is released.

## Checks that run without a phone

- `tests/ServerAddressTest.java` — plain Java test of the LAN address
  validation (compile with any JDK, run `java ServerAddressTest`).
- The Java sources compile against `android.jar` (platform 34).
- Everything on a real phone: see `TEST_CHECKLIST.md`.
