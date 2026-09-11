# PyInstaller spec for PDF OCR Reader.
#
# Build (from the repo root, in a CLEAN venv — see packaging/BUILD.md):
#   .venv-build\Scripts\python -m PyInstaller packaging/pdf_ocr_reader.spec --noconfirm --clean
#
# Output: dist/PdfOcrReader/PdfOcrReader.exe (onedir — the whole folder is
# what Inno Setup installs).

import os

from PyInstaller.utils.hooks import collect_data_files

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

# rapidocr ships its ONNX models + default config.yaml as package data; no
# PyInstaller hook collects them automatically.
datas = collect_data_files("rapidocr")

a = Analysis(
    [os.path.join(REPO_ROOT, "packaging", "run_gui.py")],
    pathex=[os.path.join(REPO_ROOT, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pdf_ocr_reader.gui.mainwindow",
        "pdf_ocr_reader.gui.pageview",
        "pdf_ocr_reader.gui.worker",
        "pdf_ocr_reader.gui.config",
        "pdf_ocr_reader.gui.app",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # rapidocr statically references these alternate inference backends; we
        # only use its onnxruntime engine. Cutting the branch here stops a build
        # from a less-clean venv dragging in torch/tensorflow/etc.
        "rapidocr.inference_engine.pytorch",
        "rapidocr.inference_engine.paddle",
        "rapidocr.inference_engine.openvino",
        "rapidocr.inference_engine.tensorrt",
        "rapidocr.inference_engine.mnn",
        "torch",
        "tensorflow",
        "paddle",
        "openvino",
        # Qt modules the app never imports.
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtNetwork",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PdfOcrReader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(REPO_ROOT, "packaging", "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="PdfOcrReader",
)
