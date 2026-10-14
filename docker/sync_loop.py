"""Run one sync at a time; retry on the next interval without browser interaction."""
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

stop = threading.Event()
signal.signal(signal.SIGTERM, lambda *_: stop.set())
signal.signal(signal.SIGINT, lambda *_: stop.set())
interval = int(os.environ.get('SYNC_INTERVAL_SECONDS', '900'))
if interval < 60:
    raise SystemExit('SYNC_INTERVAL_SECONDS must be at least 60')
script = Path(__file__).with_name('timetree_sync.py')
while not stop.is_set():
    started = time.monotonic()
    print(datetime.now(timezone.utc).isoformat(), 'TimeTree sync gestartet', flush=True)
    try:
        result = subprocess.run([sys.executable, str(script), 'sync', '--live'], timeout=600)
        if result.returncode:
            print('Sync fehlgeschlagen; letzter erfolgreicher Stand bleibt verfügbar. '
                  'Bei abgelaufener Sitzung Secret erneuern.', flush=True)
    except subprocess.TimeoutExpired:
        print('Sync nach 10 Minuten abgebrochen; erneuter Versuch im nächsten Intervall.', flush=True)
    stop.wait(max(0, interval - (time.monotonic() - started)))
