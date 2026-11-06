#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -f backup.zip ]; then
  echo 'backup.zip absent à la racine : aucune mutation effectuée.' >&2
  exit 1
fi
docker compose run --rm app python3 /app/scripts/restore.py
