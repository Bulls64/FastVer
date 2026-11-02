#!/usr/bin/env bash
# Télécharge un fichier et vérifie son empreinte SHA-256 avant toute utilisation (point A2 de l'audit).
# Downloads a file and checks its SHA-256 checksum before any use (audit item A2).
#
#   fetch_verified.sh <url> <sha256 attendu / expected> <fichier de sortie / output file>
#
# Empreinte vide ou différente → échec, sauf avec PIN_PRINT=1 : l'empreinte est alors seulement affichée
# (pour épingler une nouvelle version). Rien n'est publié dans ce mode : la release ne part que sur un tag.
# Empty or different checksum → failure, except with PIN_PRINT=1: the checksum is then only printed
# (to pin a new version). Nothing is published in that mode: the release only goes out on a tag.
set -euo pipefail
url=$1; want=${2,,}; out=$3
mkdir -p "$(dirname "$out")"
curl -fsSL --retry 3 -o "$out" "$url"
got=$(sha256sum "$out" | cut -d' ' -f1)
echo "SHA-256 $got  $(basename "$url")"
if [ "$got" = "$want" ]; then
  exit 0
fi
if [ "${PIN_PRINT:-}" = "1" ]; then
  echo "::warning::Empreinte non vérifiée (PIN_PRINT) / checksum not enforced: $(basename "$url") = $got"
  exit 0
fi
echo "::error::Empreinte inattendue / unexpected checksum for $url: attendu/expected '${want:-(vide/empty)}', obtenu/got $got" >&2
rm -f "$out"
exit 1
