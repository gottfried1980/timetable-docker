# Docker architecture

For setup instructions, see [INSTALL.md](INSTALL.md).

The Compose stack contains two Linux services:

- `display`: serves the dashboard and a live media index on port 3000 inside
  the container (published as port 8080 by default). JSON Server runs internally
  on port 3001. The proxy handles `/media-list.json` directly to prevent stale
  static lists from hiding personal media.
- `sync`: runs a one-way TimeTree import on startup and every 15 minutes.
  It reads the encrypted session and key from separate Docker secrets.

The named `timetable_data` volume stores `/data/db.json`. Only the display
service mounts it. The sync service updates data through the display API.
The `media` directory is mounted read-only into the display service; secrets
are mounted only into the sync service. Both services run as UID/GID 1000.

Frontend requests use the browser's current origin, allowing NAS clients to
access the same host without hardcoded localhost URLs. The root URL serves
`index.html`. Application assets and the media index use no-store cache headers.

TimeTree event identity uses `externalId`; JSON Server assigns local IDs on
creation. Existing copies of the same external event are reconciled by the
sync, and the frontend suppresses repeated copies with matching identity.
Distinct external events with the same title/time remain separate.

No Windows scheduler or credential manager is required inside Docker.
Encrypted session data is decrypted in memory using the separately mounted
key. Protect the key, cookie, NAS ACLs and backups. The dashboard has no native
login; use a trusted local network or an authenticated reverse proxy/VPN.

The distributed `.env.example` contains placeholders and paths only.
Your `.env`, database, photos, music, keys and sessions are excluded from Git
and the release archive. The Docker build context uses an explicit allowlist.

Docker secrets documentation:
https://docs.docker.com/compose/how-tos/use-secrets/
