#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
docker compose run --rm app sh -c 'cd /app && composer install --no-interaction'
docker compose run --rm app sh -c 'cd /app && composer check-platform-reqs'
