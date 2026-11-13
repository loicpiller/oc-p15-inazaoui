#!/bin/sh
set -eu
umask 002
mkdir -p /app/vendor /app/var
if [ ! -d /app/public/uploads ]; then
    mkdir -p /app/public/uploads
    chown www-data:www-data /app/public/uploads
fi
# Named volumes start as root; the web process and CLI share www-data.
chown -R www-data:www-data /app/vendor /app/var
if ! gosu www-data test -w /app/public/uploads; then
    echo "public/uploads must be writable by www-data (UID 33); configure host permissions." >&2
    exit 1
fi
if [ "${1:-}" = frankenphp ] && [ ! -f /app/vendor/autoload.php ]; then
    echo 'Dependencies missing: run docker compose run --rm app composer install first.' >&2
    exit 1
fi
# /app is a host bind mount owned by a different UID; prevents git dubious-ownership errors.
git config --system --replace-all safe.directory /app
exec gosu www-data "$@"
