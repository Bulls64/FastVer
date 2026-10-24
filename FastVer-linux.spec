# -*- mode: python ; coding: utf-8 -*-
# Recette PyInstaller de FastVer pour Linux : un dossier (empaqueté ensuite en AppImage par tools/build_appimage.sh).
# PyInstaller recipe of FastVer for Linux: a folder (then packed into an AppImage by tools/build_appimage.sh).
# Compilation / build :  python -m PyInstaller --noconfirm --clean FastVer-linux.spec
import os
import re
import subprocess

# Modules Qt et bibliothèques inutiles à FastVer, retirés pour alléger l'AppImage.
# Qt modules and libraries FastVer doesn't need, removed to slim down the AppImage.
DROP_PREFIXES = (
    "libqeglfs", "libqlinuxfb", "libqminimal", "libqminimalegl", "libqvnc", "libqvkkhrdisplay", "libqoffscreen",
    "libQt6EglFS", "libQt6Network", "libQt6Pdf", "libQt6Quick", "libQt6Qml", "libQt6VirtualKeyboard",
    "libQt6WaylandCompositor", "libQt6WaylandEgl", "libqtvirtualkeyboard",
    "libqicns", "libqtga", "libqtiff", "libqwbmp", "libqpdf",   # WebP gardé : fonds d'écran de Fedora…
                                                                    # WebP kept: Fedora wallpapers…
    "QtNetwork", "libqcertonlybackend", "libqopensslbackend", "libqgnutlsbackend",
)
# Bibliothèques de base présentes sur toute distribution de bureau : les embarquer (depuis la machine de
# compilation) provoquerait des conflits avec celles du système (pilotes graphiques, thèmes, polices…).
# Inspiré de la liste d'exclusion standard des AppImage.
# Base libraries present on every desktop distribution: bundling them (from the build machine) would clash
# with the system's own (graphics drivers, themes, fonts…). Based on the standard AppImage exclude list.
SYSTEM_LIBS = (
    "libc.so", "libm.so", "libdl.so", "libpthread.so", "librt.so", "libresolv.so", "ld-linux",
    "libstdc++.so", "libgcc_s.so", "libGL", "libEGL", "libGLX", "libGLdispatch", "libOpenGL", "libdrm.so",
    "libgbm.so", "libX11", "libxcb.so", "libXau.so", "libXdmcp.so", "libXext.so", "libXrender.so",
    "libfontconfig.so", "libfreetype.so", "libharfbuzz.so", "libexpat.so", "libz.so",
    "libdbus-1.so", "libsystemd.so", "libudev.so", "libgcrypt.so", "libgpg-error.so", "libcap.so",
    "liblzma.so", "libzstd.so", "liblz4.so", "libbz2.so", "libbrotli", "libpng16.so", "libbsd.so", "libmd.so",
    "libglib-2.0.so", "libgobject-2.0.so", "libgio-2.0.so", "libgmodule-2.0.so", "libgthread-2.0.so",
    "libpcre2", "libffi.so", "libmount.so", "libblkid.so", "libselinux.so", "libuuid.so",
    "libwayland-client.so", "libwayland-cursor.so", "libwayland-egl.so",
    "libgtk-3.so", "libgdk-3.so", "libcairo", "libpango", "libatk", "libatspi", "libepoxy.so", "libgdk_pixbuf",
)
DROP_DIRS = ("platformthemes/libqgtk3", "egldeviceintegrations", "wayland-graphics-integration-server", "tls", "networkinformation",
             "qmltooling", "position", "sqldrivers", "multimedia", "printsupport")

a = Analysis(
    ["fastver.py"],
    excludes=["tkinter", "_tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick"],
    noarchive=False,
    optimize=0,
)


def keep(entry):
    name, path = os.path.basename(entry[0]), entry[0].replace("\\", "/")
    if name.startswith(DROP_PREFIXES) or name.startswith(SYSTEM_LIBS) or "libqgtk3" in name:
        return False
    return not any(f"/plugins/{d}/" in path for d in DROP_DIRS)


def needed(path):
    """Bibliothèques demandées par un fichier ELF (entrées NEEDED). / Libraries an ELF file asks for (NEEDED)."""
    out = subprocess.run(["readelf", "-d", path], capture_output=True, text=True).stdout
    return set(re.findall(r"\(NEEDED\).*\[(.+?)\]", out))


a.binaries = [b for b in a.binaries if keep(b)]
# Ne garder que les bibliothèques réellement utilisées par ce qui reste : PyInstaller a aussi ramassé les
# dépendances des modules retirés (GTK → pango, krb5…), devenues orphelines.
# Keep only the libraries actually used by what remains: PyInstaller also picked up the dependencies of the
# removed modules (GTK → pango, krb5…), now orphaned.
by_name = {os.path.basename(b[0]): b for b in a.binaries}
roots = [b for b in a.binaries if "/" in b[0].replace("\\", "/") or not os.path.basename(b[0]).startswith("lib")
         or os.path.basename(b[0]).startswith(("libpython", "libpyside6", "libshiboken6", "libQt6"))]
seen, todo = set(), list(roots)
while todo:
    b = todo.pop()
    if b[0] in seen:
        continue
    seen.add(b[0])
    todo += [by_name[n] for n in needed(b[1]) if n in by_name]
dropped = sorted(os.path.basename(b[0]) for b in a.binaries if b[0] not in seen)
print("Bibliothèques orphelines retirées / orphaned libraries removed:", ", ".join(dropped) or "aucune")
a.binaries = [b for b in a.binaries if b[0] in seen]
a.datas = [d for d in a.datas if keep(d) and "/translations/" not in d[0].replace("\\", "/")]
pyz = PYZ(a.pure)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FastVer", debug=False, strip=True, upx=False,
          console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=True, upx=False, name="FastVer")
