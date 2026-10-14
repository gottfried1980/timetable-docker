# Installation guide

## Requirements

- A Linux NAS/server with Docker Engine and Docker Compose v2.
- An x86-64 or ARM64 system supported by the Node and Python base images.
- A TimeTree account accessible in a desktop browser.
- Python 3 on your setup computer to encrypt the session cookie.
- A TV or computer connected to the same network as the NAS.

## 1. Extract the project

Extract the archive into your chosen project directory, for example:

```text
/volume1/docker/timetable-docker/
```

`compose.yaml`, `index.html` and the `docker` directory must be directly inside
that folder. Avoid accidentally creating another nested project folder.
No personal media, database or credentials are shipped in the archive.

Copy `.env.example` to `.env`. This is a plain configuration file, not a Python
virtual environment. Set `TIMETREE_CALENDAR` to the code at the end of your
TimeTree calendar URL, for example `https://timetreeapp.com/calendars/YOUR_CODE`.

```dotenv
DISPLAY_PORT=8080
DISPLAY_BIND_ADDRESS=0.0.0.0
TIMETREE_CALENDAR=YOUR_CODE
TIMETREE_SECRET_PATH=./secrets/timetree_session.enc
TIMETREE_KEY_PATH=./keys/timetree.key
```

Only paths and non-secret settings belong here. Do not put passwords, cookies
or encryption key values in `.env`.

## 2. Encrypt your TimeTree session

On your setup computer, install the encryption dependency:

```sh
python -m pip install -r requirements-sync.txt
```

Sign in to TimeTree in a desktop browser. Open developer tools, then
**Application/Storage → Cookies → https://timetreeapp.com** and copy only the
value of `_session_id`. Treat this cookie like a password; do not share it in
chat, commit it or paste it into a command-line argument.

Create encrypted credentials using the hidden prompt:

```sh
python prepare-secret.py --key-file ./keys/timetree.key
```

On Linux, your Python command may be `python3` instead of `python`.
This creates `secrets/timetree_session.enc` and `keys/timetree.key`.
Transfer them to the corresponding folders on the NAS. The Windows credential
manager is not needed by the containers. If you already stored a Windows
session, you can export it directly without a plaintext cookie file:

```powershell
python prepare-secret.py --from-windows --key-file .\keys\timetree.key
```

To migrate an existing plaintext session file:

```sh
python prepare-secret.py --key-file ./keys/timetree.key --migrate ./secrets/timetree_session.txt
```

The plaintext file is removed only after successful encryption and verification.
Existing copies, snapshots and backups are not removed by this command.

## 3. Restrict permissions

From the project directory on the NAS:

```sh
sudo chown 1000:1000 keys/timetree.key secrets/timetree_session.enc
sudo chmod 600 keys/timetree.key secrets/timetree_session.enc
sudo chmod 700 keys secrets
```

The sync container runs as UID/GID 1000 and needs read access to both files.
NAS ACLs should also exclude unrelated users. Store the key separately from
ciphertext backups, preferably in a protected encrypted NAS folder. To use an
external key folder, set its absolute file path in `.env`.

The session is decrypted in memory. An administrator who can access the key
and encrypted session can still decrypt it. Protect and back up the key; losing
it requires creating a new encrypted session with a new key.

## 4. Build and start

```sh
cd /volume1/docker/timetable-docker
sudo docker compose config --quiet
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=50 sync
```

The display service must become healthy. The sync service runs immediately and
every 15 minutes. The initial import may take a while for large calendars.

Open this address on your TV or computer:

```text
http://YOUR_NAS_IP:8080/
```

Do not use `127.0.0.1` on your TV: that address refers to the TV itself.
No version/query parameter is required. The NAS frontend and API share the
same origin; application files are served without browser caching.

## 5. Add optional photos and music

Place your own files directly in these folders:

```text
media/photos/    JPG, JPEG, PNG, WebP
media/music/     MP3, M4A, OGG, WAV
```

Subfolders and GIF/HEIC files are currently not indexed. The Docker server reads
the folders directly when the media list is requested. Reload the dashboard
after adding media; no Python indexing command is needed on the NAS.
Files must be readable by the container. In a suitably protected media share,
directories 755 and media files 644 are a common setup. Do not apply these
permissions to encryption keys or session secrets.

The photo slideshow advances every 20 seconds and can be paused. Music attempts
autoplay; if the TV browser blocks audible playback, press **Musik starten**
once. Pausing is respected and the playlist repeats. There are no external
video or music players.

## 6. Verify the installation

Run on the NAS:

```sh
curl -I http://127.0.0.1:8080/
curl -sS http://127.0.0.1:8080/version.json
curl -sS http://127.0.0.1:8080/media-list.json
curl -sS http://127.0.0.1:8080/timeTreeSync
```

Expected: HTTP 200, the installed release, populated media arrays if files were
added, and a timestamp after a successful sync. You can inspect `/events` to
see the saved calendar data; it contains private event details.

If media arrays are empty:

```sh
sudo docker compose exec display ls -l /app/public/media/photos /app/public/media/music
```

If files are missing there, check the bind mount and project directory. If files
are visible, check their formats and the display service logs. Keep the existing
database and secrets while diagnosing problems.

## Updates

Preserve `.env`, `media`, `keys`, `secrets` and the Docker database volume.
Overwrite only the application files, then:

```sh
sudo docker compose stop sync
sudo docker compose build display sync
sudo docker compose up -d --force-recreate display sync
```

The display build verifies the frontend against `release-manifest.json` and
fails if release files were mixed. Verify `/version.json` after updating.
Changing hashed source files manually requires regenerating the manifest.

## Expired session

Sign in again on your desktop, then rerun `prepare-secret.py` with the existing
key. Replace the encrypted session file on the NAS and recreate the sync service:

```sh
sudo docker compose up -d --force-recreate sync
```

An import failure leaves the previous data available. A partial write failure
may apply some changes; the next successful sync reconciles them. Sync identity
uses TimeTree's `externalId`, not JSON Server's generated local `id`.

## Backups and migration

Stop services before exporting a consistent database backup:

```sh
sudo docker compose stop
sudo docker compose run --rm --no-deps -T --entrypoint sh display -c 'cat /data/db.json' > db-backup.json
sudo docker compose up -d
```

To import an existing `db.json` (replaces the NAS database):

```sh
sudo docker compose stop
sudo docker compose run --rm --no-deps -T --entrypoint sh display -c 'cat > /data/db.json' < db.json
sudo docker compose up -d
```

Back up media and the encryption key separately. Use the same Compose project
name during updates so the existing named volume is reused. **Never use
`docker compose down -v` unless you intend to delete the database.**

## Clean rebuild and removal

`cleanup-nas.sh` removes only this project's containers, network and locally
built images. The database volume, `media`, `keys`, `secrets` and `.env` are
kept. Use it before a clean rebuild (for example after changing a Dockerfile)
or to take the project off the NAS without losing data:

```sh
cd /volume1/docker/timetable-docker
sh cleanup-nas.sh
sudo docker compose up -d --build   # only if you want to rebuild
```

The script refuses to run outside `/volume1/docker/timetable-docker` or when
`compose.yaml` is missing, so it cannot hit another Compose project by
accident. It runs `docker compose down --remove-orphans --rmi local` without
`-v`, so appointments and tasks survive and reappear after the next start. To
delete the database as well, follow the warning in the backups section above.

## Tests and deployment status

Python sync/encryption tests, browser tests and a real local JSON Server
integration test cover the main application behavior. A full Linux Docker
image build must still be verified on a working Docker host; the development
machine's Docker daemon was unavailable. Vercel cannot run this Compose stack
unchanged; this installation guide is for Docker on a NAS/Linux server.
