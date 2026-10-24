# -*- mode: python ; coding: utf-8 -*-
# Recette PyInstaller de FastVer.exe : un seul fichier, sans console, allégé des parties de Qt inutiles.
# PyInstaller recipe for FastVer.exe: single file, no console, stripped of unneeded Qt parts.
# Compilation / build :  python tools/make_version_info.py
#                        python -m PyInstaller --noconfirm --clean FastVer.spec
import os

# Fichiers binaires retirés : FastVer n'en a pas besoin (et l'exe passe ainsi sous 30 Mo).
# Binaries removed: FastVer doesn't need them (and the exe drops below 30 MB).
DROP = {
    "opengl32sw.dll",                                       # OpenGL logiciel de secours / software OpenGL fallback
    "qdirect2d.dll", "qminimal.dll", "qoffscreen.dll",      # moteurs d'affichage inutilisés / unused platform plugins
    "qt6network.dll", "qtnetwork.pyd",                      # QtNetwork : jamais chargé / never loaded
    "qcertonlybackend.dll", "qopensslbackend.dll", "qschannelbackend.dll",  # TLS de QtNetwork / QtNetwork TLS
    "qicns.dll", "qtga.dll", "qtiff.dll", "qwbmp.dll",      # formats d'image exotiques / exotic image formats
}

a = Analysis(
    ["fastver.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter", "unittest", "pydoc", "PySide6.QtNetwork"],
    noarchive=False,
    optimize=0,
)
a.binaries = [b for b in a.binaries if os.path.basename(b[0]).lower() not in DROP]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FastVer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon="fastver.ico",
    version="version_info.txt",
)
