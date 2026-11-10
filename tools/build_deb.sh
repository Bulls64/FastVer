#!/usr/bin/env bash
# Construit le paquet fastver_<version>_amd64.deb à partir du dossier PyInstaller déjà préparé pour l'AppImage.
# Builds the fastver_<version>_amd64.deb package from the PyInstaller folder already prepared for the AppImage.
#
# À lancer après tools/build_appimage.sh (qui laisse build/FastVer.AppDir), ou avec BUNDLE=<dossier> pointant
# sur un dossier contenant FastVer et _internal (par exemple celui d'une AppImage extraite).
# Run after tools/build_appimage.sh (which leaves build/FastVer.AppDir), or with BUNDLE=<folder> pointing at a
# folder holding FastVer and _internal (for instance the one of an extracted AppImage).
#
# Installé / installed :  /usr/lib/fastver/            le programme / the program
#                         /usr/bin/fastver             lien vers le programme / link to the program
#                         /usr/bin/fastver-cli         lien qui ouvre directement le mode console / opens console mode
#                         /usr/share/applications/fastver.desktop, icône / icon (hicolor 256×256)
# Les mises à jour passent par apt / dpkg : dans cette forme, FastVer ne remplace pas ses propres fichiers
# (forme « frozen ») et propose seulement la page de la version.
# Updates go through apt / dpkg: in this form, FastVer doesn't replace its own files (“frozen” form) and only
# offers the release page.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
BUNDLE=${BUNDLE:-$ROOT/build/FastVer.AppDir/usr/lib/fastver}
[ -x "$BUNDLE/FastVer" ] && [ -d "$BUNDLE/_internal" ] || {
  echo "✗ Dossier du programme introuvable / program folder not found : $BUNDLE" >&2; exit 1; }

VERSION=$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' fastver.py)
[ -n "$VERSION" ] || { echo "✗ APP_VERSION introuvable dans fastver.py / not found" >&2; exit 1; }
case "$(uname -m)" in x86_64) ARCH=amd64 ;; aarch64) ARCH=arm64 ;; *) ARCH=$(uname -m) ;; esac
OUT="$ROOT/release/fastver_${VERSION}_${ARCH}.deb"

echo "▶ Arborescence du paquet / package tree (fastver $VERSION, $ARCH)"
PKG="$ROOT/build/deb"
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/lib" "$PKG/usr/bin" "$PKG/usr/share/applications" \
  "$PKG/usr/share/icons/hicolor/256x256/apps" "$PKG/usr/share/doc/fastver"
cp -a "$BUNDLE" "$PKG/usr/lib/fastver"
# Rien d'écrivable par d'autres que root, rien d'exécutable sans raison.
# Nothing writable by anyone but root, nothing executable without a reason.
find "$PKG/usr" -type d -exec chmod 755 {} +
find "$PKG/usr" -type f -exec chmod 644 {} +
chmod 755 "$PKG/usr/lib/fastver/FastVer"
ln -s ../lib/fastver/FastVer "$PKG/usr/bin/fastver"
ln -s ../lib/fastver/FastVer "$PKG/usr/bin/fastver-cli"   # nom contenant « cli » → mode console
                                                          # name containing “cli” → console mode
sed 's/^Exec=.*/Exec=fastver/' linux/fastver.desktop > "$PKG/usr/share/applications/fastver.desktop"
install -m 644 linux/fastver.png "$PKG/usr/share/icons/hicolor/256x256/apps/fastver.png"
mkdir -p "$PKG/usr/share/man/man1"
cat <<EOF | gzip -9n > "$PKG/usr/share/man/man1/fastver.1.gz"
.TH FASTVER 1 "" "FastVer $VERSION" "User Commands"
.SH NAME
fastver, fastver-cli \\- "About" window for Fastfetch, in the Windows 11 Winver style
.SH SYNOPSIS
.B fastver
.RI [ options ]
.br
.B fastver-cli
.RI [ options ]
.SH DESCRIPTION
.B fastver
shows the system information gathered by
.BR fastfetch (1)
in a window styled after Winver (Windows 11).
.B fastver-cli
(or
.BR "fastver --cli" )
prints the same information in the terminal.
.SH OPTIONS
.TP
.B --cli
Console mode; see
.B fastver --cli --help
for its options (--specs, --json, --no-color, --check, --update...).
.TP
.B --demo
Sample data, without running Fastfetch.
.TP
.B --version
Print the version and exit.
.SH FILES
.I ~/.cache/FastVer/fastver.log
.SH NOTES
Installed from a .deb package, FastVer is updated through apt or dpkg: it never replaces its own files and
only points to the release page.
.SH SEE ALSO
.BR fastfetch (1),
https://github.com/Bulls64/FastVer
EOF
ln -s fastver.1.gz "$PKG/usr/share/man/man1/fastver-cli.1.gz"
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
DEPENDS="libc6 (>= 2.34), libstdc++6, libgcc-s1, zlib1g, libzstd1, libglib2.0-0t64 | libglib2.0-0, \
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
