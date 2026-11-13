#!/usr/bin/env python3
"""Restore the three PostgreSQL INSERT files and uploads from backup.zip."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

os.chdir('/app/public')
archive = Path('/app/backup.zip')
# PGDATABASE sets the target database (default: app).
env = dict(os.environ, PGHOST='database', PGUSER='app', PGPASSWORD='app', PGDATABASE=os.environ.get('PGDATABASE', 'app'))
target = env['PGDATABASE']
# RESTORE_VALIDATE_ONLY=1 restores data without copying files for isolated validation.
validate_only = os.environ.get('RESTORE_VALIDATE_ONLY') == '1'
TABLES = ('user', 'album', 'media')


def run(*args, **kwargs):
    return subprocess.run(args, env=env, check=True, **kwargs)


def sql(query):
    return run('psql', '-X', '-v', 'ON_ERROR_STOP=1', '-At', '-c', query, capture_output=True, text=True).stdout.strip()


def statements(text, table):
    # Split SQL statements at unquoted semicolons; psql commands and dollar quoting are rejected.
    result, buf = [], []
    i, state = 0, 'plain'
    while i < len(text):
        c = text[i]
        nxt = text[i:i+2]
        if state == 'plain':
            if nxt == '--':
                state = 'line'; i += 2; buf.append(' '); continue
            if nxt == '/*':
                state = 'comment'; i += 2; buf.append(' '); continue
            if c in "\"'":
                state = c
                escape_string = c == "'" and bool(re.search(r"(?:^|[^a-zA-Z0-9_])E$", ''.join(buf), re.I))
            elif c in '\\$':
                raise ValueError('Syntaxe SQL non prise en charge dans ' + table)
            elif c == ';':
                statement = ''.join(buf).strip()
                if not re.match(r'^INSERT\s+INTO\s+(?:public\s*\.\s*)?"?' + table + r'"?(?=\s|\()', statement, re.I):
                    raise ValueError('Instruction autre que INSERT dans ' + table)
                result.append(statement + ';\n'); buf = []; i += 1; continue
        elif state == 'line':
            if c == '\n': state = 'plain'; buf.append('\n')
            i += 1; continue
        elif state == 'comment':
            if nxt == '*/': state = 'plain'; i += 2
            else: i += 1
            continue
        else:
            if c == state:
                if i + 1 < len(text) and text[i+1] == state:
                    buf.extend([c, c]); i += 2; continue
                state = 'plain'
            elif c == '\\' and state == "'" and escape_string:
                if i + 1 >= len(text): raise ValueError('Chaîne SQL incomplète dans ' + table)
                buf.extend([c, text[i+1]]); i += 2; continue
        buf.append(c); i += 1
    if state not in ('plain', 'line') or ''.join(buf).strip() or not result:
        raise ValueError('SQL incomplet ou vide dans ' + table)
    return ''.join(result)


try:
    if not archive.is_file():
        raise ValueError('Archive /app/backup.zip absente : aucune mutation effectuée')
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory(prefix='restore-') as tmp:
        tmp = Path(tmp)
        members = []
        for item in z.infolist():
            parts = item.filename.split('/')
            if '__MACOSX' in parts or any(p == '.DS_Store' or p.startswith('._') for p in parts) or item.is_dir():
                continue
            if item.filename.startswith('/') or '\\' in item.filename or any(p in ('', '.', '..') for p in parts):
                raise ValueError('Chemin d’archive invalide : ' + item.filename)
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Lien symbolique refusé : ' + item.filename)
            members.append(item)
        dumps = {}
        for item in members:
            name = PurePosixPath(item.filename).name.lower()
            if name in {t + '.sql' for t in TABLES}:
                table = name[:-4]
                if table in dumps: raise ValueError('Fichier SQL en double : ' + name)
                dumps[table] = statements(z.read(item).decode('utf-8-sig'), table)
        if set(dumps) != set(TABLES):
            raise ValueError('Les trois fichiers user.sql, album.sql et media.sql sont requis')
        staged = tmp / 'uploads'
        staged.mkdir()
        uploads = set()
        for item in members:
            parts = PurePosixPath(item.filename).parts
            if 'uploads' not in parts: continue
            tail = parts[parts.index('uploads') + 1:]
            if not tail: continue
            rel = PurePosixPath(*tail)
            if rel in uploads: raise ValueError('Upload en double : ' + str(rel))
            uploads.add(rel)
            staged_path = staged.joinpath(*tail)
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as source, staged_path.open('xb') as output:
                shutil.copyfileobj(source, output)
        if not uploads: raise ValueError('Aucun fichier uploads trouvé dans l’archive')
        for _ in range(60):
            if subprocess.run(['pg_isready', '-h', 'database', '-U', 'app', '-d', 'app'], env=env, stdout=subprocess.DEVNULL).returncode == 0: break
            time.sleep(1)
        else: raise RuntimeError('PostgreSQL indisponible')
        # Validate-only must never reach the app database by mistake.
        if validate_only and target == 'app':
            raise RuntimeError('RESTORE_VALIDATE_ONLY exige un PGDATABASE explicite et différent de app')
        if sql("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')") != '0':
            raise RuntimeError('La base contient déjà des objets ; restauration refusée')
        # psql and Doctrine may resolve different databases (test env appends _test); check both before any mutation.
        psql_db = sql('SELECT current_database()')
        probe = subprocess.run(('php', '/app/bin/console', 'dbal:run-sql', 'SELECT current_database()'), env=env, capture_output=True, text=True)
        lines = [line.strip() for line in (probe.stdout or probe.stderr).strip().splitlines() if line.strip() and set(line.strip()) != {'-'}]
        if probe.returncode != 0 or not lines:
            raise RuntimeError('Vérification Doctrine impossible : ' + (lines[-1] if lines else 'aucune sortie'))
        doctrine_db = lines[-1]
        if psql_db != target or doctrine_db != target:
            raise RuntimeError(f'Cible incohérente : PGDATABASE={target}, psql={psql_db}, Doctrine={doctrine_db} ; restauration refusée')
        dest = Path('/app/public/uploads')
        if not validate_only and (dest.is_symlink() or not dest.is_dir() or any(p.name != '.gitignore' or p.is_symlink() for p in dest.iterdir())):
            raise RuntimeError('Le dossier uploads est absent, lié ou non vide ; restauration refusée')
        print('Création du schéma Doctrine local...', flush=True)
        run('php', '/app/bin/console', 'doctrine:schema:create', '--no-interaction')
        data = tmp / 'data.sql'
        with data.open('w', encoding='utf-8') as out:
            out.write('BEGIN;\n')
            for table in TABLES: out.write(dumps[table])
            out.write("DO $$ BEGIN IF (SELECT count(*) FROM album) != 5 OR (SELECT count(*) FROM \"user\") != 101 OR (SELECT count(*) FROM media) != 5050 THEN RAISE EXCEPTION 'Comptages inattendus'; END IF; END $$;\n")
            for table in TABLES:
                out.write(f"SELECT setval('public.{table}_id_seq'::regclass, COALESCE((SELECT MAX(id) FROM \"{table}\"), 1), EXISTS(SELECT 1 FROM \"{table}\"));\n")
            out.write('COMMIT;\n')
        with data.open('rb') as source: run('psql', '-X', '-v', 'ON_ERROR_STOP=1', stdin=source)
        paths = sql('SELECT path FROM media').splitlines()
        missing = []
        for path in paths:
            parts = path.split('/')
            if len(parts) < 2 or parts[0] != 'uploads' or any(p in ('', '.', '..') for p in parts) or '\\' in path or PurePosixPath(*parts[1:]) not in uploads:
                missing.append(path)
        if missing: raise RuntimeError(f'{len(missing)} chemins média absents ou invalides : {missing[:5]}')
        if not validate_only:
            for rel in uploads:
                path = dest.joinpath(*rel.parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                with (staged / rel).open('rb') as source, path.open('xb') as output: shutil.copyfileobj(source, output)
            print('Restauration vérifiée : 5 albums, 101 utilisateurs, 5050 médias, fichiers présents.')
        else:
            print('Validation isolée vérifiée : 5 albums, 101 utilisateurs, 5050 médias, chemins conformes à l\'archive ; aucune copie de fichiers.')
except (Exception, KeyboardInterrupt) as exc:
    sys.exit(f'Restauration interrompue : {exc}. Si le schéma ou des fichiers ont été créés, état partiel : consulter docs/docker.md avant reprise.')
