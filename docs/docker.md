# Développement avec Docker

Prérequis : Docker Engine et Docker Compose, accès réseau aux registres et à Composer. Le serveur est uniquement local : <http://localhost:8080>. Pour choisir un autre port, exporter `HTTP_PORT=8081` avant les commandes Compose. PostgreSQL n'expose aucun port hôte. Les identifiants et secrets de Compose sont uniquement destinés au développement local.

```sh
docker compose build
./scripts/install.sh                 # composer install avec dépendances dev, puis check-platform-reqs
docker compose up -d
./scripts/restore.sh                 # facultatif : exige ./backup.zip
```

L'installation équivalente sans script est :

```sh
docker compose run --rm app sh -c 'cd /app && composer install --no-interaction'
docker compose run --rm app sh -c 'cd /app && composer check-platform-reqs'
```

Le code et `public/uploads` sont montés depuis le dossier local ; les volumes nommés `vendor`, `var` et `database` contiennent respectivement les dépendances, le cache et les données PostgreSQL. Serveur et commandes tournent sous le même utilisateur `www-data`, avec umask 002 ; les fichiers créés dans les uploads doivent rester accessibles depuis l'hôte. Sur Linux, si nécessaire, autoriser l'UID du conteneur à écrire dans `public/uploads` par groupe ou ACL. Ne pas ouvrir les permissions à tous. Les variables Compose remplacent `.env` aussi pour la CLI ; aucun fichier `.env` n'est modifié.

```sh
docker compose logs -f app database
docker compose exec -w /app app composer show symfony/framework-bundle
docker compose exec -w /app app composer check-platform-reqs
docker compose exec app php /app/bin/console about
docker compose exec app php /app/bin/console debug:router
docker compose exec -w /app app vendor/bin/phpunit
docker compose restart
docker compose down                   # conserve les volumes et les uploads
```

PHPUnit ne trouve actuellement aucun test dans le dépôt. Le compte de développement est `ina` / `password`.

## Restauration

Placer l'archive locale non suivie `backup.zip` à la racine après l'installation. Elle doit contenir exactement un fichier de chaque nom `user.sql`, `album.sql` et `media.sql`, avec des instructions PostgreSQL `INSERT INTO` pour la table correspondante, ainsi que des fichiers sous un dossier `uploads`. Les fichiers peuvent être rangés dans des sous-dossiers de l'archive. Les instructions sont analysées avant toute création de schéma ; les commandes psql, le dollar quoting et les formats SQL autres que des INSERT ne sont pas acceptés. L'archive et son SQL doivent provenir d'une source fiable.

Le script vérifie l'archive et prépare les uploads dans un dossier temporaire, attend PostgreSQL, refuse une base contenant des objets ou un dossier uploads non vide, puis crée le schéma depuis les mappings Doctrine. Il importe user, album et media dans une transaction PostgreSQL, vérifie 5 albums, 101 utilisateurs et 5050 médias et recale leurs séquences. Il vérifie ensuite que chaque chemin de média correspond à un fichier extrait sous `public/uploads`, avant de copier les fichiers. Les métadonnées macOS sont ignorées ; les chemins d'archive dangereux, doublons et liens symboliques sont refusés.

En cas d'échec après création du schéma, la base peut contenir le schéma seul ou les données ; une interruption pendant la copie peut aussi laisser des uploads partiels. Examiner et sauvegarder les données utiles, supprimer manuellement les seuls uploads partiels concernés, puis utiliser le reset ci-dessous avant de recommencer. Le reset conserve volontairement les uploads ; leur présence empêche une nouvelle restauration.

## Reset destructif

```sh
./scripts/reset.sh --yes
```

Cette commande arrête le projet et supprime les volumes Compose `database` (toutes les données), `vendor` et `var` (cache et logs). Elle préserve les fichiers de `public/uploads` sur l'hôte et l'archive. Pour repartir, relancer build si nécessaire, installation, démarrage et restauration. Ne pas utiliser `docker compose down -v` à la légère : il supprime les mêmes volumes.

## Chemins et limites de l'application

FrankenPHP tourne sans worker depuis `/app/public` : les chemins relatifs `uploads/...` correspondent à `public/uploads` pour la création et la suppression. Symfony retire le préfixe du nom transmis à `move`, évitant `uploads/uploads`. Le serveur ne publie que `public/`, refuse les fichiers cachés et les scripts PHP dans les uploads.

Avec une base vide, les pages nécessitant des tables échouent jusqu'à restauration. Avec des données synthétiques, la connexion `ina`, l'accès à la liste d'administration et la création persistante d'un album ont été vérifiés.
