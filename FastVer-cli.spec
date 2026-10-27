# -*- mode: python ; coding: utf-8 -*-
# Recette PyInstaller de FastVer-cli.exe : version en ligne de commande (fastver.py --cli), avec console,
# sans Qt ni QFluentWidgets. Le nom de l'exe suffit à démarrer en mode CLI.
# PyInstaller recipe for FastVer-cli.exe: command-line version (fastver.py --cli), with a console,
# without Qt or QFluentWidgets. The exe's name is enough to start in CLI mode.
# Compilation / build :  python tools/make_version_info.py
#                        python -m PyInstaller --noconfirm --clean FastVer-cli.spec

a = Analysis(
    ["fastver.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "shiboken6", "qfluentwidgets", "qframelesswindow", "darkdetect",
              "tkinter", "_tkinter", "unittest", "pydoc"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FastVer-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    icon="fastver.ico",
    version="version_info_cli.txt",
)
