# Phase 5: Installer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** One `PdfOcrReader-Setup.exe` a teammate double-clicks — no Python, no admin rights. Reuses the Refinery Doc Organizer packaging approach wholesale.

**Architecture:** A `packaging/` dir: a PyInstaller `.spec` (onedir build from a **clean venv**, bundling RapidOCR's ONNX models and excluding its unused torch/paddle/openvino/tensorrt backends), an Inno Setup `.iss` (per-user install to `%LOCALAPPDATA%\Programs`, no admin), a generated `.ico`, a bilingual first-run README.

**Spec:** `docs/superpowers/specs/2026-09-10-pdf-ocr-reader-design.md`
**Reference:** `C:\Development\Oil and Gas\refinery-doc-organizer\packaging\` (BUILD.md, doc_organizer.spec, installer.iss) — copy and adapt.

## Global Constraints

- **Build from `.venv-build`, never the shared dev Python** — rapidocr statically references heavy backends; a fat environment bloats the build to GB. (`packaging/BUILD.md` in the reference repo explains it.)
- Per-user install (`{localappdata}\Programs\PDF OCR Reader`), `PrivilegesRequired=lowest` — no IT ticket.
- Uninstall removes program files only — leaves `%LOCALAPPDATA%\PdfOcrReader` (config + OCR cache) alone.
- App/product name: **PDF OCR Reader**. Exe: `PdfOcrReader.exe`. Installer: `packaging/output/PdfOcrReader-Setup.exe`.

---

### Task 1: App icon

**Files:** Create `packaging/app.ico`, `packaging/logo.png`

- [ ] Draw a simple, clean icon with Pillow (no external asset): a teal (`#0d7d74`) rounded-square tile, a white document sheet with 3-4 grey text lines, a magnifier lens (ring + handle) overlapping the lower-right. Render at 1024×1024 to `packaging/logo.png`, then save a multi-resolution `packaging/app.ico` (`[256,128,64,48,32,16]`).

```python
from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
m = 64
d.rounded_rectangle([m, m, S - m, S - m], radius=180, fill=(13, 125, 116, 255))
# document
dx0, dy0, dx1, dy1 = 250, 210, 640, 720
d.rounded_rectangle([dx0, dy0, dx1, dy1], radius=28, fill=(248, 249, 250, 255))
for i in range(4):
    y = dy0 + 90 + i * 80
    d.line([dx0 + 55, y, dx1 - 55, y], fill=(150, 160, 170, 255), width=22)
# magnifier
cx, cy, r = 640, 640, 180
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 255), width=46)
d.ellipse([cx - r + 46, cy - r + 46, cx + r - 46, cy + r - 46], fill=(13, 125, 116, 90))
d.line([cx + 120, cy + 120, cx + 250, cy + 250], fill=(255, 255, 255, 255), width=60)
img.save("packaging/logo.png")
img.save("packaging/app.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
```

- [ ] Eyeball `logo.png` — legible, not ugly. Adjust proportions if needed. Commit.

```bash
git add packaging/app.ico packaging/logo.png
git commit -m "packaging: app icon (document + magnifier, teal tile)"
```

---

### Task 2: PyInstaller spec + entry script

**Files:** Create `packaging/run_gui.py`, `packaging/doc_organizer.spec` → `packaging/pdf_ocr_reader.spec`, `.gitignore` update

- [ ] `packaging/run_gui.py`:
```python
"""PyInstaller entry point."""
import sys

from pdf_ocr_reader.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] `packaging/pdf_ocr_reader.spec` — adapt the reference spec:
  - `REPO_ROOT` from `os.path.dirname(os.path.abspath(SPEC))` + `..`
  - `datas = collect_data_files("rapidocr")` (the ONNX models + config.yaml)
  - Analysis script: `packaging/run_gui.py`; `pathex=[<repo>/src]`
  - `hiddenimports`: `pdf_ocr_reader.gui.mainwindow`, `.pageview`, `.worker`, `.config`, `.app`
  - `excludes`: `rapidocr.inference_engine.pytorch` / `.paddle` / `.openvino` / `.tensorrt` / `.mnn`, `torch`, `tensorflow`, `paddle`, `openvino`, plus the Qt modules we don't use: `PySide6.QtQml`, `PySide6.QtQuick`, `PySide6.QtNetwork`, `PySide6.QtMultimedia`, `PySide6.QtWebEngineCore`, `PySide6.QtWebEngineWidgets`, `PySide6.QtPdf`, `PySide6.QtPdfWidgets`, `PySide6.Qt3D*`
  - `EXE(... name="PdfOcrReader", console=False, icon=<repo>/packaging/app.ico)`
  - `COLLECT(... name="PdfOcrReader")`

- [ ] `.gitignore` — add `/build/`, `/dist/`, `packaging/output/`, `.venv-build/` if not already there.

- [ ] Commit the spec + entry.

```bash
git add packaging/run_gui.py packaging/pdf_ocr_reader.spec .gitignore
git commit -m "packaging: PyInstaller onedir spec"
```

---

### Task 3: Clean-venv build + smoke

- [ ] From the repo root:
```bash
rm -rf build dist .venv-build
py -3 -m venv .venv-build
.venv-build\Scripts\python -m pip install -q -e . pyinstaller pyinstaller-hooks-contrib
.venv-build\Scripts\python -m pip list  | grep -iE "torch|tensorflow|sklearn"   # expect nothing
.venv-build\Scripts\python -m PyInstaller packaging\pdf_ocr_reader.spec --noconfirm --clean
```
- [ ] `du -sh dist/PdfOcrReader` — expect ~350-450 MB, not GB. If GB, check `build/pdf_ocr_reader/warn-*.txt`, add the offender to `excludes`, rebuild.
- [ ] Smoke: `dist\PdfOcrReader\PdfOcrReader.exe` — window opens (or with `QT_QPA_PLATFORM=offscreen` for a headless check it exits cleanly after a moment). Verify `dist\PdfOcrReader\_internal\rapidocr\models\*.onnx` present and `_internal\PySide6\plugins\platforms\qwindows.dll` present.
- [ ] Open a real scanned PDF through the built exe (drag onto it, or `PdfOcrReader.exe "path.pdf"`), confirm OCR + search + highlight work in the frozen build.

(No commit — build output is gitignored.)

---

### Task 4: Inno Setup installer

**Files:** Create `packaging/installer.iss`, `packaging/README-first-run.txt`, `packaging/README-first-run.id.txt`, `packaging/BUILD.md`

- [ ] `packaging/installer.iss` — adapt the reference:
  - `#define MyAppName "PDF OCR Reader"`, `MyAppExeName "PdfOcrReader.exe"`, `MyAppVersion "0.1.0"`, publisher "RU VI Balongan - Process Engineering"
  - unique `AppId` GUID
  - `DefaultDirName={localappdata}\Programs\{#MyAppName}`, `PrivilegesRequired=lowest`
  - `[Files]`: `..\dist\PdfOcrReader\*` recursive; both READMEs (`.id.txt` with `isreadme`, `.txt` plain)
  - `[Icons]`: Start Menu + optional desktop (a `desktopicon` task)
  - `[Run]`: launch after install (`nowait postinstall skipifsilent`)
  - `SetupIconFile=app.ico`, `OutputDir=output`, `OutputBaseFilename=PdfOcrReader-Setup`, `Compression=lzma2/max`

- [ ] `packaging/README-first-run.txt` (English) and `.id.txt` (Bahasa Indonesia) — short: what it is; drag a PDF onto the window or File→Open; OCR runs in the background (keep the window open, be patient on big scans); search inside; Save searchable copy for use in other readers; config + cache under `%LOCALAPPDATA%\PdfOcrReader` and survive uninstall; UI is English.

- [ ] `packaging/BUILD.md` — the two build commands (clean-venv PyInstaller, then `ISCC.exe packaging\installer.iss`), the clean-venv rule, the icon-regeneration snippet, version-bump note.

- [ ] Compile: `"C:\Users\Ridho\AppData\Local\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss` → `packaging\output\PdfOcrReader-Setup.exe`.

- [ ] Commit the packaging text files.

```bash
git add packaging/installer.iss packaging/README-first-run.txt packaging/README-first-run.id.txt packaging/BUILD.md
git commit -m "packaging: Inno Setup installer + bilingual first-run guide + BUILD.md"
```

---

### Task 5: Installer validation

- [ ] Silent-install to a scratch dir:
```
PdfOcrReader-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="C:\...\test_install"
```
- [ ] Launch the installed exe (offscreen or real) — opens.
- [ ] Open a real scanned PDF through it — OCR + search + highlight + export all work.
- [ ] Run the installed `unins000.exe /VERYSILENT` — install dir emptied; `%LOCALAPPDATA%\PdfOcrReader` still present.
- [ ] Record: installer size, install/launch/uninstall results, wall-clock for OCR on a real page in the frozen build. Append to this plan; commit.

```bash
git add docs/superpowers/plans/2026-09-11-phase5-installer.md
git commit -m "docs: record Phase 5 installer validation"
```

---

## Self-Review

Reuse of a proven setup. The one real risk — a fat build from a dirty
environment — is handled by the clean-venv rule + defensive `excludes`.
Product naming is consistent (`PDF OCR Reader` / `PdfOcrReader.exe` /
`PdfOcrReader-Setup.exe` / `%LOCALAPPDATA%\PdfOcrReader`). Uninstall
preserves user data. No placeholders.
