# Android test checklist

**Status: NOT RUN BY AGENT.** The build environment has no Android phone or
emulator, so nothing on this list has been run on a device. The owner runs
it on the shop phone and ticks the boxes. (What WAS verified without a
phone: the Java sources compile against platform 34, the ServerAddress unit
test passes 19/19 on a desktop JDK, and the APK signature verifies after
the manual build — see BUILD_APK.md.)

Setup: PC program running (START_MEDIGEN.bat), phone on the same Wi-Fi.

- [ ] App installs and opens.
- [ ] First run asks for the server address; a public address (e.g. 8.8.8.8)
      is refused with a clear message; the shop PC address is accepted.
- [ ] Login works, and "Remember me" keeps the user logged in after the
      app is closed and reopened.
- [ ] A wrong address / PC off shows "Server not reachable" with the setup
      screen and a working retry.
- [ ] Back button goes back inside the program before closing the app.
- [ ] Rotating the phone does not lose the bill being made.
- [ ] Turning Wi-Fi off shows the not-reachable screen; turning it back on
      and retrying recovers.
- [ ] Camera barcode scan on the New Sale page asks for camera permission
      once, then scans; denying permission leaves typing fully usable.
- [ ] A full sale can be completed on the phone (add items, complete,
      invoice opens).
- [ ] The app icon and name show as "MediGen AI Pro" with the shop logo.
