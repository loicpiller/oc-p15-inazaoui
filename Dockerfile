FROM composer:2.9.5 AS composer
FROM dunglas/frankenphp:1.13.2-php8.2-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends git unzip zip postgresql-client python3 gosu \
    && rm -rf /var/lib/apt/lists/* \
    && install-php-extensions intl mbstring pdo_pgsql
COPY --from=composer /usr/bin/composer /usr/local/bin/composer
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY docker/entrypoint.sh /usr/local/bin/project-entrypoint
RUN chmod +x /usr/local/bin/project-entrypoint
WORKDIR /app/public
ENTRYPOINT ["project-entrypoint"]
CMD ["frankenphp", "run", "--config", "/etc/caddy/Caddyfile"]
