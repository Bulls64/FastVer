#!/usr/bin/env bash
# Construit FastVer-x86_64.AppImage : PyInstaller (dossier) → AppDir → appimagetool.
# Builds FastVer-x86_64.AppImage: PyInstaller (folder) → AppDir → appimagetool.
#
# Prérequis / requirements : python -m pip install -r requirements-build.txt,
#   python -m pip install --no-deps -r requirements-nodeps.txt, readelf et objdump (binutils),
#   appimagetool (variable APPIMAGETOOL, sinon téléchargé / otherwise downloaded).
# Options : LEGACY_LIBS=<dossier>  bibliothèques plus anciennes à substituer (glibc plus basse)
#                                  older libraries to substitute (lower glibc requirement)
#           RUNTIME=<fichier>      runtime AppImage local au lieu de le télécharger / local AppImage runtime
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PY=${PYTHON:-python3}
ARCH=$(uname -m)
OUT="$ROOT/release/FastVer-$ARCH.AppImage"

echo "▶ PyInstaller"
"$PY" -m PyInstaller --noconfirm --clean FastVer-linux.spec

if [ -n "${LEGACY_LIBS:-}" ]; then
  echo "▶ Bibliothèques substituées / substituted libraries ($LEGACY_LIBS)"
  for lib in dist/FastVer/_internal/*.so*; do
    name=$(basename "$lib")
    alt=$(find "$LEGACY_LIBS" -name "$name*" -type f | head -1)
    [ -n "$alt" ] && cp -L "$alt" "$lib" && echo "  $name"
  done
fi

echo "▶ AppDir"
APPDIR="$ROOT/build/FastVer.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a dist/FastVer "$APPDIR/usr/lib/fastver"
cp linux/fastver.desktop "$APPDIR/fastver.desktop"
cp linux/fastver.desktop "$APPDIR/usr/share/applications/fastver.desktop"
cp linux/fastver.png "$APPDIR/fastver.png"
cp linux/fastver.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/fastver.png"
ln -s fastver.png "$APPDIR/.DirIcon"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
# Point d'entrée de l'AppImage / AppImage entry point
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/fastver/FastVer" "$@"
RUN
chmod +x "$APPDIR/AppRun"

echo "▶ glibc minimale exigée / minimum glibc required"
GLIBC=$(find "$APPDIR" -type f \( -name "*.so*" -o -name FastVer \) -exec objdump -T {} + 2>/dev/null \
  | grep -oE "GLIBC_[0-9]+\.[0-9]+" | sort -u -V | tail -1 | cut -d_ -f2)
MAX=${MAX_GLIBC:-2.34}   # minimum déjà imposé par Qt 6.12 / minimum already required by Qt 6.12
echo "  glibc $GLIBC (limite / limit $MAX)"
if [ "$(printf '%s\n%s\n' "$GLIBC" "$MAX" | sort -V | tail -1)" != "$MAX" ]; then
  echo "✗ Une bibliothèque embarquée exige glibc $GLIBC > $MAX : l'AppImage ne marcherait pas partout." >&2
  echo "✗ A bundled library requires glibc $GLIBC > $MAX: the AppImage wouldn't run everywhere." >&2
  exit 1
fi

echo "▶ appimagetool"
TOOL=${APPIMAGETOOL:-}
if [ -z "$TOOL" ]; then
  TOOL="$ROOT/build/appimagetool"
  curl -sSL -o "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
  chmod +x "$TOOL"
fi
mkdir -p "$ROOT/release"
RT=()
[ -n "${RUNTIME:-}" ] && RT=(--runtime-file "$RUNTIME")
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=$ARCH "$TOOL" --no-appstream "${RT[@]}" "$APPDIR" "$OUT"
chmod +x "$OUT"
ls -l "$OUT"
