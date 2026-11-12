#!/usr/bin/env bash
# Construit le paquet fastver_<version>_<amd64|arm64>.deb à partir du dossier PyInstaller déjà préparé pour l'AppImage.
# Builds the fastver_<version>_<amd64|arm64>.deb package from the PyInstaller folder already prepared for the AppImage.
#
# À lancer après tools/build_appimage.sh (qui laisse build/FastVer.AppDir), ou avec BUNDLE=<dossier> pointant
# sur un dossier contenant FastVer et _internal (par exemple celui d'une AppImage extraite).
# Run after tools/build_appimage.sh (which leaves build/FastVer.AppDir), or with BUNDLE=<folder> pointing at a
# folder holding FastVer and _internal (for instance the one of an extracted AppImage).
#
# Arborescence commune : tools/linux_tree.sh. / Shared tree: tools/linux_tree.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PKG="$ROOT/build/deb"
source "$ROOT/tools/linux_tree.sh"
case "$(uname -m)" in x86_64) ARCH=amd64 ;; aarch64) ARCH=arm64 ;; *) ARCH=$(uname -m) ;; esac
OUT="$ROOT/release/fastver_${VERSION}_${ARCH}.deb"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/share/doc/fastver"
# Programme PyInstaller autonome : bibliothèques embarquées et lanceur sans PIE, voulus.
# Self-contained PyInstaller program: bundled libraries and a non-PIE launcher, on purpose.
mkdir -p "$PKG/usr/share/lintian/overrides"
cat > "$PKG/usr/share/lintian/overrides/fastver" <<'EOF'
fastver: embedded-library *
fastver: hardening-no-pie *
fastver: shared-library-lacks-prerequisites *
EOF

cat > "$PKG/usr/share/doc/fastver/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: FastVer
Source: https://github.com/Bulls64/FastVer

Files: *
Copyright: $(date +%Y) Bulls64
License: GPL-3.0-or-later
 The full text of the license is in /usr/share/common-licenses/GPL-3.
 Le paquet embarque Python, Qt 6 (PySide6, LGPL-3.0) et QFluentWidgets (GPL-3.0).
 The package bundles Python, Qt 6 (PySide6, LGPL-3.0) and QFluentWidgets (GPL-3.0).
EOF
{
  echo "fastver ($VERSION) stable; urgency=medium"
  echo
  echo "  * Release $VERSION: https://github.com/Bulls64/FastVer/releases/tag/v$VERSION"
  echo
  echo " -- Bulls64 <Bulls64@users.noreply.github.com>  $(date -R)"
} | gzip -9n > "$PKG/usr/share/doc/fastver/changelog.gz"

# Dépendances : bibliothèques que l'AppImage laisse au système (voir SYSTEM_LIBS dans FastVer-linux.spec).
# Les alternatives couvrent les noms de Debian 12+ et d'Ubuntu 22.04+ (passage à t64 en 24.04).
# Dependencies: libraries the AppImage leaves to the system (see SYSTEM_LIBS in FastVer-linux.spec).
# The alternatives cover Debian 12+ and Ubuntu 22.04+ names (t64 rename in 24.04).
DEPENDS="libc6 (>= $GLIBC_MIN), libstdc++6, libgcc-s1, zlib1g, libzstd1, libglib2.0-0t64 | libglib2.0-0, \
libfontconfig1, libfreetype6, libdbus-1-3, libx11-6, libx11-xcb1, libxcb1, libegl1, libgl1, libdrm2, \
libwayland-client0, libwayland-cursor0, libwayland-egl1"
SIZE=$(du -sk --apparent-size "$PKG/usr" | cut -f1)
cat > "$PKG/DEBIAN/control" <<EOF
Package: fastver
Version: $VERSION
Architecture: $ARCH
Maintainer: Bulls64 <Bulls64@users.noreply.github.com>
Installed-Size: $SIZE
Depends: $DEPENDS
Recommends: fastfetch
Section: utils
Priority: optional
Homepage: https://github.com/Bulls64/FastVer
Description: "About" window for Fastfetch, in the Windows 11 Winver style
 FastVer shows the system information gathered by Fastfetch in a window
 styled after Winver (Windows 11): ASCII logo, specifications, light and
 dark themes with an acrylic material. "fastver-cli" (or "fastver --cli")
 prints the same information in the terminal.
 .
 Fenêtre « À propos » pour Fastfetch, dans le style de Winver (Windows 11).
EOF
( cd "$PKG" && find usr -type f -print0 | sort -z | xargs -0 md5sum > DEBIAN/md5sums )

echo "▶ dpkg-deb"
mkdir -p "$ROOT/release"
dpkg-deb --root-owner-group -Zxz --build "$PKG" "$OUT"
dpkg-deb --info "$OUT" | sed -n '1,/^ Description/p'
ls -l "$OUT"
