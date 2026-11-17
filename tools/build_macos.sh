#!/usr/bin/env bash
# Construit FastVer.app et FastVer-macos-arm64.dmg sur un Mac Apple Silicon (macOS 14 ou plus).
# Builds FastVer.app and FastVer-macos-arm64.dmg on an Apple Silicon Mac (macOS 14 or later).
#
# Prérequis / requirements :  python3 -m pip install -r requirements-build.txt -r requirements-macos.txt
#                             python3 -m pip install --no-deps -r requirements-nodeps.txt
#
# L'appli est signée « ad hoc » (sans certificat Apple) : au premier lancement, macOS demande de l'ouvrir
# depuis Réglages Système → Confidentialité et sécurité → « Ouvrir quand même ».
# The app is “ad hoc” signed (no Apple certificate): on first launch, macOS asks to open it from
# System Settings → Privacy & Security → “Open Anyway”.
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo "✗ Mac Apple Silicon requis / required" >&2; exit 1; }
PY=${PYTHON:-python3}

echo "▶ Icône / icon"
rm -rf build/FastVer.iconset && mkdir -p build/FastVer.iconset
for s in 16 32 64 128 256; do
  sips -z $s $s linux/fastver.png --out "build/FastVer.iconset/icon_${s}x${s}.png" >/dev/null
  [ $s -le 128 ] && sips -z $((s * 2)) $((s * 2)) linux/fastver.png \
    --out "build/FastVer.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns build/FastVer.iconset -o build/FastVer.icns

echo "▶ PyInstaller"
"$PY" -m PyInstaller --noconfirm --clean FastVer-macos.spec
APP=dist/FastVer.app
lipo -archs "$APP/Contents/MacOS/FastVer"
codesign --verify --deep --strict "$APP" && echo "✓ signature ad hoc valide / valid ad hoc signature"
"$APP/Contents/MacOS/FastVer" --version

echo "▶ Image disque / disk image"
mkdir -p release
rm -rf build/dmg && mkdir -p build/dmg
ditto "$APP" build/dmg/FastVer.app   # ditto garde tout ce que la signature couvre / keeps all the signature covers
codesign --verify --deep --strict --verbose=2 build/dmg/FastVer.app
ln -s /Applications build/dmg/Applications
rm -f release/FastVer-macos-arm64.dmg
hdiutil create -volname FastVer -srcfolder build/dmg -fs HFS+ -format UDZO -ov release/FastVer-macos-arm64.dmg
ls -l release/FastVer-macos-arm64.dmg
