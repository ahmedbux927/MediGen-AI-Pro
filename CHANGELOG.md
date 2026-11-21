# Changelog

All notable changes to MediGen AI Pro are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions
match the app version shown in Settings.

## [101.03] — 2026-11-21
### Added
- New professionally designed app icon (Windows app, installer, web, Android).
- One-click Windows app build: `MAKE_WINDOWS_APP.bat`.
### Fixed
- Permanent user deletion: references across every table are now scanned
  (including foreign keys with non-`user_id` names) and safely reassigned
  to a protected placeholder account before deletion.
- Settings backup/restore inside the packaged Windows app.
### Verified
- Full project audit — 2,509 automated tests passing, 0 failed.

## [101.02] — 2026-11-21
### Added
- `MAKE_WINDOWS_APP.bat` one-click path (PyInstaller + Inno Setup).
### Fixed
- Backup/restore commands inside the frozen (PyInstaller) app.

## [101.01] — 2026-11-21
### Added
- Theme now defaults to **System** and follows the Windows light/dark
  setting live (toggle cycles System → Light → Dark).

## [101.00] — 2026-11-21
### Added
- Pack/unit selling, import-with-preview, stock-count lifecycle,
  barcode label printing, user editing, settings reset-to-defaults.
- Single generated stylesheet build (`scripts/build_css.py`).
- Android companion: LAN-only address validation, camera permission bridge.
### Verified
- 38-route role-based QA matrix (Admin / Pharmacist / Cashier / anonymous).
