# NAS quick start

Complete instructions: [INSTALL.md](INSTALL.md).

1. Extract the project directly into `/volume1/docker/timetable-docker`.
2. Copy `.env.example` to `.env` and set your own `TIMETREE_CALENDAR`.
3. Create encrypted credentials following the installation guide.
4. Copy ciphertext to `secrets/timetree_session.enc` and its matching key to
   `keys/timetree.key`. Set owner 1000:1000 and file permissions 600.
5. Start the stack:

```sh
cd /volume1/docker/timetable-docker
sudo docker compose config --quiet
sudo docker compose up -d --build
sudo docker compose logs --tail=50 sync
```

Open **http://YOUR_NAS_IP:8080/**. No version suffix is required.

Add your own photos to `media/photos` and local music to `media/music`.
The archive contains no personal media or credentials.

## Updating an existing installation

Keep your `.env`, media, keys, sessions and database volume. Replace only the
application files and use the same Compose project name as before.

```sh
sudo docker compose stop sync
sudo docker compose build display sync
sudo docker compose up -d --force-recreate display sync
curl -sS http://127.0.0.1:8080/version.json
```

## Removing a failed deployment

Only if you want to remove this project's containers and locally built images:

```sh
sudo docker compose down --remove-orphans --rmi local
```

This retains the named database volume and host media/secret files. Do not add
`-v`; do not run a global Docker prune to fix this application.
