"""Local, one-way TimeTree -> json-server sync. No third-party dependencies."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import getpass
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

def configured_calendar():
    value = os.environ.get('TIMETREE_CALENDAR')
    if value:
        return value
    configuration = Path(__file__).resolve().parent / '.env'
    if configuration.exists():
        for line in configuration.read_text(encoding='utf-8-sig').splitlines():
            if line.startswith('TIMETREE_CALENDAR='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''


CALENDAR = configured_calendar()
SECRET = 'TodoListe/TimeTree'
SESSION_SECRET = 'TodoListe/TimeTreeSession'
DEFAULT_DB = Path(__file__).resolve().parent.parent / 'todo_backend' / 'db.json'


class SyncError(Exception):
    pass


class Credential(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
        ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
        ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)),
        ('Persist', wintypes.DWORD), ('AttributeCount', wintypes.DWORD),
        ('Attributes', ctypes.c_void_p), ('TargetAlias', wintypes.LPWSTR),
        ('UserName', wintypes.LPWSTR),
    ]


def credential_api():
    if os.name != 'nt':
        raise SyncError('Die Secret-Verwaltung benötigt Windows.')
    api = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(ctypes.POINTER(Credential))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    return api


def store_credentials(email, password, target=SECRET):
    blob = password.encode('utf-16-le')
    if not email or not password or len(blob) > 2560:
        raise SyncError('Bitte eine E-Mail und ein gültiges Passwort eingeben.')
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    credential = Credential()
    credential.Type = 1  # CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.UserName = email
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = buffer
    credential.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE, current Windows user
    if not credential_api().CredWriteW(ctypes.byref(credential), 0):
        raise SyncError('Windows konnte die Zugangsdaten nicht speichern.')


def read_credentials(target=SECRET):
    api = credential_api()
    pointer = ctypes.POINTER(Credential)()
    if not api.CredReadW(target, 1, 0, ctypes.byref(pointer)):
        raise SyncError('Zugangsdaten fehlen. Zuerst: python timetree_sync.py setup')
    try:
        credential = pointer.contents
        password = ctypes.string_at(credential.CredentialBlob,
                                    credential.CredentialBlobSize).decode('utf-16-le')
        return credential.UserName, password
    finally:
        api.CredFree(pointer)


def request_json(opener, url, payload=None, method='GET'):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=data, method=method, headers={
        'Content-Type': 'application/json', 'Accept': 'application/json',
        'X-Timetreea': 'web/2.1.0/en',
    })
    try:
        with opener.open(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Report only the operation and a numeric internal code, never raw bodies.
        operation = 'Anmeldung' if '/auth/' in url else 'Kalenderabruf'
        detail = ''
        try:
            body = json.loads(error.read(8192))
            code = body.get('code') if isinstance(body, dict) else None
            if isinstance(code, int) and not isinstance(code, bool):
                detail = f' (interner Code {code})'
        except (ValueError, OSError):
            pass
        hint = ('Direkter Login wurde abgelehnt. Nutze: python timetree_sync.py setup-session'
                if operation == 'Anmeldung' else
                'Kalenderzugriff prüfen. Bei HTTP 401/403 die Browsersitzung mit setup-session erneuern.')
        raise SyncError(f'{operation}: HTTP {error.code}{detail}. {hint}') from None
    except (urllib.error.URLError, TimeoutError):
        raise SyncError('TimeTree ist nicht erreichbar. Internetverbindung prüfen.') from None
    except (ValueError, UnicodeError):
        raise SyncError('TimeTree hat keine gültige JSON-Antwort geliefert.') from None


def wait_for_login_fields(page):
    # DOMContentLoaded precedes hydration of TimeTree's JavaScript login form.
    email_selector = 'input[type="email"], input[name="email"], input[autocomplete="username"]'
    password_selector = 'input[type="password"]'
    page.wait_for_function("""({emailSelector, passwordSelector}) => {
        const visible = selector => [...document.querySelectorAll(selector)]
            .filter(el => el.getClientRects().length && !el.disabled);
        return visible(emailSelector).length === 1 && visible(passwordSelector).length === 1;
    }""", arg={'emailSelector': email_selector, 'passwordSelector': password_selector}, timeout=30000)
    return (page.locator('input[type="email"]:visible, input[name="email"]:visible, input[autocomplete="username"]:visible'),
            page.locator('input[type="password"]:visible'))


def browser_login(calendar, headless=False):
    try:
        from playwright.sync_api import sync_playwright, Error as BrowserError
    except ImportError:
        raise SyncError('Browser-Modul fehlt. Installieren mit: python -m pip install -r requirements-browser.txt') from None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=headless)
            try:
                # Ephemeral context: no persistent profile, traces or cookie files.
                context = browser.new_context(locale='de-DE')
                page = context.new_page()
                page.goto('https://timetreeapp.com/signin', wait_until='domcontentloaded', timeout=45000)
                if headless:
                    try:
                        email_field, password_field = wait_for_login_fields(page)
                    except BrowserError:
                        raise SyncError('Loginformular nach 30 Sekunden nicht bereit. '
                                        'Mit python timetree_sync.py login-browser im sichtbaren Fenster prüfen.') from None
                    email, password = read_credentials()
                    email_field.fill(email)
                    password_field.fill(password)
                    password_field.press('Enter')
                else:
                    print('Bitte im geöffneten Edge-Fenster bei TimeTree anmelden. '
                          'Das Fenster wird nach erfolgreicher Prüfung automatisch geschlossen.')
                deadline = time.monotonic() + (60 if headless else 240)
                while time.monotonic() < deadline:
                    if page.is_closed():
                        raise SyncError('Browserfenster vor erfolgreicher Anmeldung geschlossen.')
                    candidates = [cookie for cookie in context.cookies('https://timetreeapp.com')
                                  if cookie['name'] == '_session_id' and cookie['value']]
                    if candidates:
                        response = context.request.get(
                            'https://timetreeapp.com/api/v1/calendars?since=0',
                            headers={'X-Timetreea': 'web/2.1.0/en'}, timeout=15000)
                        if response.ok:
                            metadata = response.json()
                            calendars = metadata.get('calendars') if isinstance(metadata, dict) else None
                            if isinstance(calendars, list):
                                if not any(isinstance(entry, dict) and (
                                    entry.get('alias_code') == calendar or str(entry.get('id')) == calendar
                                ) for entry in calendars):
                                    raise SyncError('Anmeldung erfolgreich, aber der gewünschte Kalender fehlt in diesem Konto.')
                                store_credentials('browser-session', candidates[0]['value'], SESSION_SECRET)
                                print('Anmeldung und Kalenderzugriff geprüft. Sitzung als Windows-Secret gespeichert.')
                                return
                    page.wait_for_timeout(1500)
                raise SyncError('Browser-Anmeldung nicht bestätigt. Ohne --headless erneut versuchen '
                                'und mögliche zusätzliche Bestätigungen im Browser abschließen.')
            finally:
                browser.close()
    except BrowserError:
        # Playwright diagnostics may contain request/cookie details; keep output generic.
        raise SyncError('Browser-Anmeldung fehlgeschlagen. Edge-Installation und Verbindung prüfen; '
                        'erneut ohne --headless versuchen.') from None


def fetch_events(email, password, calendar, session_token=None):
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    base = 'https://timetreeapp.com/api/v1'
    if session_token:
        cookies.set_cookie(http.cookiejar.Cookie(
            version=0, name='_session_id', value=session_token,
            port=None, port_specified=False, domain='timetreeapp.com',
            domain_specified=False, domain_initial_dot=False,
            path='/', path_specified=True, secure=True, expires=None,
            discard=True, comment=None, comment_url=None, rest={'HttpOnly': None},
        ))
    else:
        request_json(opener, base + '/auth/email/signin', {
            'uid': email, 'password': password, 'uuid': uuid.uuid4().hex,
        }, 'PUT')
    if not any(cookie.name == '_session_id' for cookie in cookies):
        raise SyncError('TimeTree hat keine Sitzung erstellt. Anmeldung nicht bestätigt.')
    # Browser URLs contain alias_code; event endpoints require the internal id.
    metadata = request_json(opener, base + '/calendars?since=0')
    if not isinstance(metadata, dict) or not isinstance(metadata.get('calendars'), list):
        raise SyncError('Die Kalenderliste konnte nicht gelesen werden.')
    matches = [entry for entry in metadata['calendars'] if isinstance(entry, dict)
               and (entry.get('alias_code') == calendar or str(entry.get('id')) == calendar)]
    if len(matches) != 1 or matches[0].get('id') is None:
        raise SyncError('Der ausgewählte Kalender wurde in dieser Sitzung nicht gefunden. '
                        'Prüfe, ob der Browser mit dem richtigen TimeTree-Konto angemeldet ist.')
    internal_id = urllib.parse.quote(str(matches[0]['id']), safe='')
    all_events = {}
    cursor = None
    seen_cursors = set()
    for _ in range(1000):
        url = f'{base}/calendar/{internal_id}/events/sync'
        if cursor is not None:
            url += '?' + urllib.parse.urlencode({'since': cursor})
        result = request_json(opener, url)
        if not isinstance(result, dict) or not isinstance(result.get('events'), list):
            raise SyncError('Unbekanntes TimeTree-Antwortformat; Datenbank bleibt unverändert.')
        for event in result['events']:
            if not isinstance(event, dict) or event.get('id') is None:
                raise SyncError('Ein TimeTree-Termin hat keine ID.')
            all_events[str(event['id'])] = event
        if result.get('chunk') is False:
            return list(all_events.values())
        if result.get('chunk') is not True:
            raise SyncError('Unvollständige TimeTree-Antwort; Datenbank bleibt unverändert.')
        next_cursor = result.get('since')
        # Treat since as an opaque cursor: TimeTree may return it as a string.
        if (isinstance(next_cursor, bool) or not isinstance(next_cursor, (str, int, float))
                or str(next_cursor) == '' or str(next_cursor) in seen_cursors):
            raise SyncError('TimeTree-Seiten konnten nicht vollständig gelesen werden.')
        seen_cursors.add(str(next_cursor))
        cursor = next_cursor
    raise SyncError('Zu viele TimeTree-Seiten; Synchronisierung abgebrochen.')


def iso_timestamp(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SyncError('Ungültige Zeitangabe im TimeTree-Termin.')
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        raise SyncError('Ungültige Zeitangabe im TimeTree-Termin.') from None


def normalize_events(raw_events, calendar):
    events = {}
    for raw in raw_events:
        if raw.get('deactivated_at') or raw.get('deleted_at'):
            continue
        if raw.get('id') is None or not isinstance(raw.get('title'), str):
            raise SyncError('Ungültiger TimeTree-Termin; Datenbank bleibt unverändert.')
        identifier = f'timetree-{calendar}-{raw["id"]}'
        events[identifier] = {
            'id': identifier, 'source': 'timetree', 'calendarId': calendar,
            'externalId': str(raw['id']), 'title': raw['title'],
            'startAt': iso_timestamp(raw.get('start_at')),
            'endAt': iso_timestamp(raw.get('end_at')),
            'allDay': bool(raw.get('all_day', False)),
            'startTimezone': raw.get('start_timezone') or 'Europe/Berlin',
            'recurrences': raw.get('recurrences') or [],
        }
    return sorted(events.values(), key=lambda event: event['startAt'])


def ensure_server_stopped():
    try:
        with socket.create_connection(('localhost', 3000), timeout=1):
            raise SyncError('Bitte JSON-Server auf Port 3000 zuerst mit Strg+C stoppen, '
                            'danach synchronisieren und wieder starten.')
    except (ConnectionRefusedError, TimeoutError):
        pass
    except OSError as error:
        if getattr(error, 'winerror', None) not in (10061, 10060):
            raise SyncError('Serverstatus konnte nicht geprüft werden.') from None


def save_events(db_path, events, calendar, original):
    # Compare again after the network request, before touching existing data.
    if db_path.read_bytes() != original:
        raise SyncError('db.json wurde zwischenzeitlich geändert. Bitte erneut synchronisieren.')
    data = json.loads(original.decode('utf-8-sig'))
    existing = data.get('events', [])
    if not isinstance(existing, list):
        raise SyncError('events muss in db.json eine Liste sein.')
    data['events'] = [event for event in existing
                      if not (event.get('source') == 'timetree'
                              and event.get('calendarId') == calendar)] + events
    data['timeTreeSync'] = {'calendarId': calendar,
                           'lastSyncedAt': datetime.now(timezone.utc).isoformat()}
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    # Keep an exact backup of the previous database before atomic replacement.
    backup = db_path.with_name(db_path.name + '.before-timetree.bak')
    backup.write_bytes(original)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=db_path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, db_path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def local_request(resource, payload=None, method='GET'):
    url = os.environ.get('JSON_SERVER_URL', 'http://127.0.0.1:3000').rstrip('/') + '/' + resource
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=body, method=method,
                                     headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            return json.loads(data) if data else None
    except urllib.error.HTTPError as error:
        raise SyncError(f'Lokaler JSON-Server: HTTP {error.code}. '
                        'Für --live müssen events und timeTreeSync bereits in db.json existieren. '
                        'Bei Bedarf zuerst einmal mit gestopptem Server synchronisieren.') from None
    except (urllib.error.URLError, TimeoutError):
        raise SyncError('Lokaler JSON-Server nicht erreichbar. start-server.cmd starten.') from None


def live_state():
    existing = local_request('events')
    metadata = local_request('timeTreeSync')
    if not isinstance(existing, list) or not isinstance(metadata, dict):
        raise SyncError('Ungültige lokale Kalenderdaten; Synchronisierung abgebrochen.')
    return existing


def event_identity(event):
    # JSON-server assigns its own local id on POST; use TimeTree's id for sync.
    external = event.get('externalId')
    return ('external', str(external)) if external is not None else ('local', str(event['id']))


def save_events_live(events, calendar):
    existing = live_state()
    owned = [event for event in existing
             if event.get('source') == 'timetree' and event.get('calendarId') == calendar]
    groups = {}
    for event in owned:
        groups.setdefault(event_identity(event), []).append(event)
    incoming = {event_identity(event): event for event in events}
    changed = 0
    keep_ids = set()
    for identity, event in incoming.items():
        matches = groups.get(identity, [])
        if matches:
            current = matches[0]
            identifier = str(current['id'])
            keep_ids.add(identifier)
            payload = event | {'id': current['id']}
            if payload != current:
                local_request('events/' + urllib.parse.quote(identifier, safe=''), payload, 'PUT')
                changed += 1
        else:
            local_request('events', event, 'POST')
            changed += 1
    for event in owned:
        identifier = str(event['id'])
        if identifier not in keep_ids:
            local_request('events/' + urllib.parse.quote(identifier, safe=''), method='DELETE')
            changed += 1
    local_request('timeTreeSync', {'calendarId': calendar,
                  'lastSyncedAt': datetime.now(timezone.utc).isoformat()}, 'PUT')
    return changed


def main():
    parser = argparse.ArgumentParser(description='TimeTree-Termine lokal in db.json synchronisieren.')
    parser.add_argument('command', choices=['setup', 'setup-session', 'login-browser', 'sync', 'forget'])
    parser.add_argument('--calendar', default=os.environ.get('TIMETREE_CALENDAR', CALENDAR))
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    parser.add_argument('--dry-run', action='store_true', help='Abruf testen, ohne db.json zu ändern')
    parser.add_argument('--headless', action='store_true', help='Browser-Login mit gespeicherten Zugangsdaten ohne Fenster versuchen')
    parser.add_argument('--live', action='store_true', help='Über den laufenden JSON-Server synchronisieren (für Aufgabenplanung)')
    args = parser.parse_args()
    try:
        if args.command in ('sync', 'login-browser') and not args.calendar:
            raise SyncError('Set TIMETREE_CALENDAR in .env or use --calendar YOUR_CALENDAR_CODE.')
        if args.command == 'setup':
            email = input('TimeTree E-Mail: ').strip()
            password = getpass.getpass('TimeTree Passwort (verdeckt): ')
            if password != getpass.getpass('Passwort wiederholen: '):
                raise SyncError('Die Passwörter stimmen nicht überein.')
            store_credentials(email, password)
            print('Zugangsdaten im Windows-Anmeldeinformationsmanager gespeichert.')
        elif args.command == 'login-browser':
            browser_login(args.calendar, args.headless)
        elif args.command == 'setup-session':
            print('In TimeTree anmelden. F12 -> Anwendung/Application -> Cookies -> '
                  'https://timetreeapp.com -> _session_id -> Wert kopieren.')
            token = getpass.getpass('_session_id (verdeckt eingeben, nur den Wert): ').strip()
            if not token or any(character.isspace() for character in token) or ';' in token:
                raise SyncError('Bitte nur den Cookie-Wert eingeben, keinen Cookie-Header.')
            store_credentials('browser-session', token, SESSION_SECRET)
            print('Browsersitzung als Windows-Secret gespeichert. Sie wird für sync bevorzugt.')
        elif args.command == 'forget':
            api = credential_api()
            for target in (SECRET, SESSION_SECRET):
                if not api.CredDeleteW(target, 1, 0) and ctypes.get_last_error() != 1168:
                    raise SyncError('Ein Secret konnte nicht gelöscht werden.')
            print('TimeTree-Zugangsdaten gelöscht.')
        else:
            if args.live:
                live_state()  # Fail early before contacting TimeTree if server is unavailable.
            else:
                db_path = args.db.resolve()
                original = db_path.read_bytes()
                json.loads(original.decode('utf-8-sig'))
                if not args.dry_run:
                    ensure_server_stopped()
            session_file = os.environ.get('TIMETREE_SESSION_FILE')
            if session_file:
                key_file = os.environ.get('TIMETREE_KEY_FILE')
                if key_file:
                    try:
                        from secret_crypto import decrypt_session
                        token = decrypt_session(session_file, key_file)
                    except ImportError:
                        raise SyncError('Verschlüsselungsmodul fehlt: python -m pip install -r requirements-sync.txt') from None
                else:
                    if os.name != 'nt':
                        raise SyncError('Unter Linux muss TIMETREE_KEY_FILE für das verschlüsselte Secret gesetzt sein.')
                    token = Path(session_file).read_text(encoding='utf-8-sig').strip()
                if not token or any(character.isspace() for character in token) or ';' in token:
                    raise SyncError('TimeTree-Secret fehlt oder enthält keinen gültigen Cookie-Wert.')
            elif os.name == 'nt':
                try:
                    _, token = read_credentials(SESSION_SECRET)
                except SyncError:
                    token = None
            else:
                raise SyncError('Unter Linux TIMETREE_SESSION_FILE auf die Secret-Datei setzen.')
            email, password = ('', '') if token else read_credentials()
            events = normalize_events(fetch_events(email, password, args.calendar, token), args.calendar)
            if args.dry_run:
                print(f'Abruf erfolgreich: {len(events)} Termine. db.json wurde nicht geändert.')
            elif args.live:
                changed = save_events_live(events, args.calendar)
                print(f'{len(events)} Termine synchronisiert, {changed} Änderungen. Eigene Todos bleiben erhalten.')
            else:
                ensure_server_stopped()
                save_events(db_path, events, args.calendar, original)
                print(f'{len(events)} Termine synchronisiert. Eigene Todos bleiben erhalten.')
            if any(event['recurrences'] for event in events):
                print('Hinweis: Serientermine werden als Ausgangstermin gespeichert; '
                      'Wiederholungen werden noch nicht einzeln berechnet.')
    except (SyncError, OSError, ValueError) as error:
        print(f'Fehler: {error}')
        return 1
    except (EOFError, KeyboardInterrupt):
        print('\nAbgebrochen.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
