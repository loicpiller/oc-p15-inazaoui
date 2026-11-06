#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "${1:-}" != '--yes' ] || [ "$#" -ne 1 ]; then
  echo 'Destructif : supprime les volumes Compose database, vendor et var. Les uploads sur disque sont conservés.' >&2
  echo 'Utilisation : scripts/reset.sh --yes' >&2
  exit 1
fi
docker compose down --volumes --remove-orphans
