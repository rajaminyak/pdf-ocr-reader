# Building the installer

Two steps: freeze with PyInstaller, then wrap with Inno Setup.

## 1. PyInstaller — from a clean, isolated venv

**Do not build from your day-to-day dev environment.** `rapidocr`
statically references its unused `torch`/`paddle`/`tensorrt`/`openvino`
backends; if any of those (or their huge dependency trees) happen to be
installed for another project sharing the same Python, PyInstaller pulls
them all in. A clean venv with only this project's declared dependencies
sidesteps it.

```bash
cd "PDF OCR reader"
python -m venv .venv-build
.venv-build\Scripts\pip install -e . pyinstaller pyinstaller-hooks-contrib
.venv-build\Scripts\python -m PyInstaller packaging\pdf_ocr_reader.spec --noconfirm --clean
```

Output: `dist\PdfOcrReader\` — `PdfOcrReader.exe` plus an `_internal\`
folder (all deps, RapidOCR's `.onnx` models, the Qt platform plugin).
Expect ~350-450 MB. If it's GB, something heavy leaked in — check
`build\pdf_ocr_reader\warn-pdf_ocr_reader.txt` and add the offender to the
spec's `excludes`.

Smoke-test: `dist\PdfOcrReader\PdfOcrReader.exe` opens the window; drop a
scanned PDF on it and confirm OCR + search + highlight work.

## 2. Inno Setup — one installer

Needs Inno Setup 6 (`winget install JRSoftware.InnoSetup`).

```bash
"C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

Output: `packaging\output\PdfOcrReader-Setup.exe` — the one file to hand to
teammates. Per-user install (no admin), Start Menu entry, uninstaller,
optional desktop shortcut. Uninstall leaves `%LOCALAPPDATA%\PdfOcrReader`
(config + OCR cache) intact.

Test before shipping:
```
PdfOcrReader-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /DIR="C:\some\test\path"
```
launch the installed exe, then `unins000.exe /VERYSILENT` and confirm the
install dir is emptied but the AppData folder remains.

## Regenerating the icon

`packaging/app.ico` (16-256 px) comes from a Pillow script — see
`packaging/logo.png` for the result. To change it, edit and re-run the
drawing code in the Phase 5 plan
(`docs/superpowers/plans/2026-09-11-phase5-installer.md`, Task 1).

## Version bump

Edit `#define MyAppVersion` in `packaging/installer.iss` and `version` in
`pyproject.toml` together.
