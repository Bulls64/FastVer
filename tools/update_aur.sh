#!/usr/bin/env bash
# Met la recette AUR (packaging/aur) à la version donnée : pkgver, pkgrel=1, empreinte de l'AppImage, .SRCINFO.
# Sets the AUR recipe (packaging/aur) to the given version: pkgver, pkgrel=1, AppImage checksum, .SRCINFO.
#
# Usage : tools/update_aur.sh <version> [sha256]
#   Sans sha256, l'empreinte est lue dans le SHA256SUMS de la release publiée (curl requis).
#   Without sha256, the checksum is read from the published release's SHA256SUMS (curl required).
#
# Publication sur l'AUR (compte AUR avec clé SSH) / publishing to the AUR (AUR account with an SSH key) :
#   git clone ssh://aur@aur.archlinux.org/fastver-bin.git && cp packaging/aur/{PKGBUILD,.SRCINFO} fastver-bin/
#   cd fastver-bin && git add PKGBUILD .SRCINFO && git commit -m "Update to <version>" && git push
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=${1:?version attendue / version expected (ex. 1.4.3)}
VERSION=${VERSION#v}
SHA=${2:-}
if [ -z "$SHA" ]; then
  SHA=$(curl -fsSL "https://github.com/Bulls64/FastVer/releases/download/v$VERSION/SHA256SUMS" \
        | awk '$2 == "FastVer-x86_64.AppImage" {print $1}')
fi
[[ "$SHA" =~ ^[0-9a-f]{64}$ ]] || { echo "✗ Empreinte invalide / invalid checksum : '$SHA'" >&2; exit 1; }

P=packaging/aur/PKGBUILD
sed -i -e "s/^pkgver=.*/pkgver=$VERSION/" -e "s/^pkgrel=.*/pkgrel=1/" \
       -e "s/^sha256sums=.*/sha256sums=('$SHA')/" "$P"

# .SRCINFO écrit ici pour ne pas exiger makepkg ; le test Arch du workflow le compare à makepkg --printsrcinfo.
# .SRCINFO written here so makepkg isn't required; the workflow's Arch test compares it with makepkg --printsrcinfo.
# shellcheck disable=SC1090
( source "$P"
  {
    echo "pkgbase = $pkgname"
    echo "	pkgdesc = $pkgdesc"
    echo "	pkgver = $pkgver"
    echo "	pkgrel = $pkgrel"
    echo "	url = $url"
    for a in "${arch[@]}"; do echo "	arch = $a"; done
    for l in "${license[@]}"; do echo "	license = $l"; done
    for d in "${depends[@]}"; do echo "	depends = $d"; done
    for d in "${optdepends[@]}"; do echo "	optdepends = $d"; done
    for d in "${provides[@]}"; do echo "	provides = $d"; done
    for d in "${conflicts[@]}"; do echo "	conflicts = $d"; done
    for o in "${options[@]}"; do echo "	options = $o"; done
    for s in "${source[@]}"; do echo "	source = $s"; done
    for s in "${noextract[@]}"; do echo "	noextract = $s"; done
    for s in "${sha256sums[@]}"; do echo "	sha256sums = $s"; done
    echo
    echo "pkgname = $pkgname"
  } > packaging/aur/.SRCINFO )
echo "✓ fastver-bin $VERSION-1 ($SHA)"
