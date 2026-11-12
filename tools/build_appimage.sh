#!/usr/bin/env bash
# Construit FastVer-<x86_64|aarch64>.AppImage (architecture de la machine) : PyInstaller (dossier) → AppDir → appimagetool.
# Builds FastVer-<x86_64|aarch64>.AppImage (the machine's architecture): PyInstaller (folder) → AppDir → appimagetool.
#
# Prérequis / requirements : python -m pip install -r requirements-build.txt,
#   python -m pip install --no-deps -r requirements-nodeps.txt, readelf et objdump (binutils),
#   appimagetool (variable APPIMAGETOOL, sinon téléchargé et vérifié / otherwise downloaded and verified).
# Options : LEGACY_LIBS=<dossier>  bibliothèques plus anciennes à substituer (glibc plus basse)
#                                  older libraries to substitute (lower glibc requirement)
#           RUNTIME=<fichier>      runtime AppImage local au lieu de le télécharger / local AppImage runtime
#           APPIMAGETOOL_SHA256, RUNTIME_SHA256  empreintes attendues / expected checksums
#           PIN_PRINT=1            affiche les empreintes sans les exiger / prints checksums without enforcing them
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
MAX=${MAX_GLIBC:-2.34}   # minimum déjà imposé par Qt 6.12 (2.39 pour aarch64, voir le workflow)
                         # minimum already required by Qt 6.12 (2.39 for aarch64, see the workflow)
echo "  glibc $GLIBC (limite / limit $MAX)"
if [ "$(printf '%s\n%s\n' "$GLIBC" "$MAX" | sort -V | tail -1)" != "$MAX" ]; then
  echo "✗ Une bibliothèque embarquée exige glibc $GLIBC > $MAX : l'AppImage ne marcherait pas partout." >&2
  echo "✗ A bundled library requires glibc $GLIBC > $MAX: the AppImage wouldn't run everywhere." >&2
  exit 1
fi

echo "▶ appimagetool"
TOOL=${APPIMAGETOOL:-}
if [ -z "$TOOL" ]; then
  # Version fixe et empreinte vérifiée (point A2) ; l'adresse et l'empreinte viennent du workflow.
  # Fixed version and verified checksum (item A2); the URL and checksum come from the workflow.
  TOOL="$ROOT/build/appimagetool"
  bash "$ROOT/tools/fetch_verified.sh" \
    "${APPIMAGETOOL_URL:-https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-$ARCH.AppImage}" \
    "${APPIMAGETOOL_SHA256:-ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0}" "$TOOL"
  chmod +x "$TOOL"
fi
if [ -z "${RUNTIME:-}" ]; then
  # Sans --runtime-file, appimagetool télécharge lui-même le runtime « continuous », non vérifié.
  # Without --runtime-file, appimagetool downloads the “continuous” runtime itself, unverified.
  RUNTIME="$ROOT/build/runtime-$ARCH"
  bash "$ROOT/tools/fetch_verified.sh" \
    "${RUNTIME_URL:-https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-$ARCH}" \
    "${RUNTIME_SHA256:-2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d}" "$RUNTIME"
fi
mkdir -p "$ROOT/release"
RT=(--runtime-file "$RUNTIME")
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=$ARCH "$TOOL" --no-appstream "${RT[@]}" "$APPDIR" "$OUT"
chmod +x "$OUT"
ls -l "$OUT"
