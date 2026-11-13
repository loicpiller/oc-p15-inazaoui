# Développement avec Docker

Prérequis : Docker Engine et Docker Compose. Serveur local uniquement : <http://localhost:8080> (autre port via `HTTP_PORT`). Identifiants et secrets Compose réservés au développement local.

```sh
docker compose build
./scripts/install.sh                 # composer install with dev deps, then check-platform-reqs
docker compose up -d
./scripts/restore.sh                 # optional: requires ./backup.zip
```

Le code et `public/uploads` sont montés depuis le dossier local ; les volumes `vendor`, `var` et `database` contiennent dépendances, cache et données PostgreSQL. Tout tourne sous `www-data`, umask 002 ; sur Linux, si nécessaire, donner l'accès en écriture aux uploads par groupe ou ACL, sans permissions ouvertes à tous.

```sh
docker compose logs -f app database
docker compose exec -w /app app composer check-platform-reqs
docker compose exec -T -e APP_ENV=test -w /app app vendor/bin/phpunit
docker compose restart
docker compose down                   # keeps volumes and uploads
```

PHPUnit exige `APP_ENV=test` : celui de Compose (`dev`) doit être surchargé, sinon les tests échouent. Sous `APP_ENV=test`, Doctrine ajoute le suffixe `_test` à l'URL Compose et la suite vise donc `app_test` : la peupler d'abord (voir « Base de test »), sinon `FunctionalTest` échoue. Compte de développement : `ina` / `password`.

## Base de test

`app_test` est peuplée sans fichiers depuis `backup.zip` via `scripts/restore.py` en mode validation. La base doit être vide : le script refuse tout objet public et crée lui-même le schéma. Procédure exacte, sans toucher à `app` ni aux uploads (le drop/recreate est sans danger même si `app_test` existe déjà avec des tables vides) :

```sh
# Recreate an empty app_test database (app and uploads are never touched)
docker compose exec -T database psql -U app -d app -c 'DROP DATABASE IF EXISTS app_test WITH (FORCE)' -c 'CREATE DATABASE app_test'
# Populate app_test from the archive without copying any file
docker compose run --rm -e APP_ENV=dev -e RESTORE_VALIDATE_ONLY=1 -e PGDATABASE=app_test -e DATABASE_URL='postgresql://app:app@database:5432/app_test?serverVersion=16&charset=utf8' app python3 /app/scripts/restore.py
```

`APP_ENV=dev` explicite évite le suffixe `_test` du test env. Le script vérifie, avant toute mutation, que `PGDATABASE` et `DATABASE_URL` désignent la même base, et exige en mode validation une cible explicitement différente de `app`.

## Restauration

Placer l'archive locale non suivie `backup.zip` à la racine : un fichier de chaque nom `user.sql`, `album.sql`, `media.sql` en `INSERT INTO` PostgreSQL, plus les fichiers sous un dossier `uploads` (sous-dossiers admis). Commandes psql, dollar quoting et autres formats rejetés ; source fiable exigée.

Le script refuse une base contenant des objets ou un dossier `public/uploads` non vide, vérifie l'égalité des cibles psql et Doctrine avant toute mutation, crée le schéma Doctrine, importe les trois tables en transaction (5 albums, 101 utilisateurs, 5050 médias, séquences recalées), puis vérifie chaque chemin de média avant de copier les fichiers. Chemins d'archive dangereux, doublons et liens symboliques refusés. En cas d'échec après coup : examiner la base et supprimer manuellement les uploads partiels, puis reset avant de recommencer.

## Reset destructif

```sh
./scripts/reset.sh --yes
```

Supprime les volumes `database` (toutes les données), `vendor` et `var`, préserve `public/uploads` et l'archive. Attention : `docker compose down -v` fait pareil.

## Chemins et limites

FrankenPHP tourne sans worker depuis `/app/public` ; les chemins relatifs `uploads/...` correspondent à `public/uploads`. Le serveur ne publie que `public/` et refuse fichiers cachés et scripts PHP dans les uploads. Avec une base vide, les pages nécessitant des tables échouent jusqu'à restauration.

## Doctrine

Le plancher PHP de `composer.json` (`>= 8.2`) reflète le minimum réel de DBAL 4.5 ; vérifier chaque montée par `composer why-not <paquet>` et garder `composer audit` vierge. `identity_generation_preferences` (séquence `{table}_id_seq`) préserve les schémas créés avant DBAL 4 ; `use_savepoints` a été retiré (toujours actif en DBAL 4).
