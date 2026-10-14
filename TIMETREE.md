# Windows setup and TimeTree sync

For the recommended NAS deployment, use [INSTALL.md](INSTALL.md).

## Configure your calendar

Copy `.env.example` to `.env` and set `TIMETREE_CALENDAR` to your own calendar
code. The code is the final segment of the TimeTree calendar URL.

## Local Windows authentication

The optional desktop setup can use Windows Credential Manager:

```powershell
python timetree_sync.py setup
python -m pip install -r requirements-browser.txt
python timetree_sync.py login-browser
```

Complete sign-in in the separate Edge window. The verified session is stored
as a Windows credential. If available, a headless attempt can use stored
credentials with `login-browser --headless`. Browser challenges may still
require interactive sign-in.

## Sync without stopping the local server

Once the events collection exists, keep JSON Server running and execute:

```powershell
python timetree_sync.py sync --live
```

For a first offline import, stop JSON Server and run
`python timetree_sync.py sync`, then restart it. Offline mode writes to
`../todo_backend/db.json` by default and backs up the previous file.

Optional Windows Task Scheduler setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-sync-task.ps1
```

The task runs every 15 minutes under the signed-in Windows user. JSON Server
must be running. Check `sync-task.log` for the latest outcome. The NAS sync
container replaces this scheduler and Windows credential storage.

To export a Windows session for Docker:

```powershell
python -m pip install -r requirements-sync.txt
python prepare-secret.py --from-windows --key-file .\keys\timetree.key
```

Do not share cookie/key values. The encrypted session needs its matching key.
Recurring events currently keep their original stored occurrence; repeated
occurrences are not expanded. This uses an unofficial TimeTree web interface
that may change or require renewed authentication.
