#!/usr/bin/env bash
# Arborescence commune aux paquets .deb et .rpm, à sourcer après avoir défini ROOT et PKG (dossier à remplir).
# Définit VERSION et remplit $PKG/usr à partir du dossier PyInstaller préparé pour l'AppImage.
# Tree shared by the .deb and .rpm packages, to be sourced after setting ROOT and PKG (folder to fill).
# Sets VERSION and fills $PKG/usr from the PyInstaller folder prepared for the AppImage.
#
# Installé / installed :  /usr/lib/fastver/            le programme / the program
#                         /usr/bin/fastver             lien vers le programme / link to the program
#                         /usr/bin/fastver-cli         lien qui ouvre directement le mode console / opens console mode
#                         /usr/share/applications/fastver.desktop, icône / icon (hicolor 256×256), man fastver
# Les mises à jour passent par le gestionnaire de paquets : dans cette forme, FastVer ne remplace pas ses propres
# fichiers (forme « frozen ») et propose seulement la page de la version.
# Updates go through the package manager: in this form, FastVer doesn't replace its own files (“frozen” form)
# and only offers the release page.
BUNDLE=${BUNDLE:-$ROOT/build/FastVer.AppDir/usr/lib/fastver}
[ -x "$BUNDLE/FastVer" ] && [ -d "$BUNDLE/_internal" ] || {
  echo "✗ Dossier du programme introuvable / program folder not found : $BUNDLE" >&2; exit 1; }

VERSION=$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' fastver.py)
[ -n "$VERSION" ] || { echo "✗ APP_VERSION introuvable dans fastver.py / not found" >&2; exit 1; }

# glibc minimale exigée par le programme : 2.34 pour x86_64, 2.39 pour aarch64 (roues PySide6 manylinux_2_39).
# Minimum glibc required by the program: 2.34 for x86_64, 2.39 for aarch64 (PySide6 manylinux_2_39 wheels).
GLIBC_MIN=$(find "$BUNDLE" -type f \( -name "*.so*" -o -name FastVer \) -exec objdump -T {} + 2>/dev/null \
  | grep -oE "GLIBC_[0-9]+\.[0-9]+" | sort -u -V | tail -1 | cut -d_ -f2)
[ -n "$GLIBC_MIN" ] || { echo "✗ glibc minimale indéterminée (objdump, paquet binutils) / minimum glibc unknown" >&2; exit 1; }
echo "  glibc >= $GLIBC_MIN"

echo "▶ Arborescence du paquet / package tree (fastver $VERSION)"
rm -rf "$PKG"
mkdir -p "$PKG/usr/lib" "$PKG/usr/bin" "$PKG/usr/share/applications" \
  "$PKG/usr/share/icons/hicolor/256x256/apps"
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
Installed from a .deb or .rpm package, FastVer is updated through the package manager: it never replaces its own files and
only points to the release page.
.SH SEE ALSO
.BR fastfetch (1),
https://github.com/Bulls64/FastVer
EOF
ln -s fastver.1.gz "$PKG/usr/share/man/man1/fastver-cli.1.gz"
