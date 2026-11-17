# -*- mode: python ; coding: utf-8 -*-
# Recette PyInstaller de FastVer.app (macOS, Apple Silicon) : appli en dossier, allégée des parties de Qt inutiles.
# PyInstaller recipe for FastVer.app (macOS, Apple Silicon): folder app, stripped of unneeded Qt parts.
# Compilation / build :  bash tools/build_macos.sh   (icône, appli, vérification de la signature, .dmg)
#                                                     (icon, app, signature check, .dmg)
import os
import re

with open("fastver.py", encoding="utf-8") as f:
    VERSION = re.search(r'^APP_VERSION = "([^"]+)"', f.read(), re.M).group(1)

# Fichiers retirés : FastVer n'en a pas besoin. / Files removed: FastVer doesn't need them.
DROP = {
    "libqminimal.dylib", "libqoffscreen.dylib",               # moteurs d'affichage inutilisés / unused platforms
    "QtNetwork", "QtNetwork.abi3.so",                         # QtNetwork : jamais chargé / never loaded
    "libqtga.dylib", "libqtiff.dylib", "libqwbmp.dylib", "libqicns.dylib",  # formats exotiques / exotic formats
}                                                              # (libqmacheif reste : fonds d'écran HEIC de macOS)
                                                               # (libqmacheif stays: macOS HEIC wallpapers)

a = Analysis(
    ["fastver.py"],
    excludes=["tkinter", "_tkinter", "unittest", "pydoc", "PySide6.QtNetwork"],
    noarchive=False,
    optimize=0,
)
a.binaries = [b for b in a.binaries if os.path.basename(b[0]) not in DROP]
a.datas = [d for d in a.datas if "/translations/" not in d[0].replace("\\", "/")]
pyz = PYZ(a.pure)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FastVer", debug=False, strip=False, upx=False,
          console=False, argv_emulation=False, target_arch="arm64")
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="FastVer")
app = BUNDLE(
    coll,
    name="FastVer.app",
    icon="build/FastVer.icns",
    bundle_identifier="io.github.bulls64.fastver",
    version=VERSION,
    info_plist={
        "CFBundleName": "FastVer",
        "CFBundleDisplayName": "FastVer",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "14.0",           # minimum de Qt 6.12 / Qt 6.12 minimum
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,    # suit le mode sombre / follows dark mode
        "NSHumanReadableCopyright": "GPL-3.0-or-later — github.com/Bulls64/FastVer",
    },
)
