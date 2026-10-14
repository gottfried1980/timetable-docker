import json
import io
from pathlib import Path
import tempfile
import unittest
import os
import sys
from unittest.mock import patch

import timetree_sync as sync


class SyncTests(unittest.TestCase):
    def test_live_sync_matches_external_id_and_removes_only_duplicate_copies(self):
        incoming=sync.normalize_events([self.event()],sync.CALENDAR)[0]
        first=incoming | {'id':'random-local-1'}
        duplicate=incoming | {'id':'random-local-2'}
        distinct=incoming | {'id':'random-local-3','externalId':'43'}
        other=incoming | {'id':'other-calendar','calendarId':'other'}
        with patch.object(sync,'live_state',return_value=[first,duplicate,distinct,other]), patch.object(sync,'local_request') as request:
            second=incoming | {'externalId':'43'}
            self.assertEqual(sync.save_events_live([incoming,second],sync.CALENDAR),1)
            self.assertEqual(request.call_args_list[0].args,('events/random-local-2',))
            self.assertEqual(request.call_args_list[0].kwargs,{'method':'DELETE'})
            self.assertEqual(request.call_count,2)

    def test_linux_sync_uses_secret_file_without_windows_credentials(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            secret = Path(folder) / 'session.txt'
            secret.write_text('fake-session\n', encoding='utf-8')
            with patch.dict(os.environ, {'TIMETREE_SESSION_FILE': str(secret)}), \
                    patch.object(sys, 'argv', ['sync', 'sync', '--live', '--dry-run', '--calendar', 'demo-calendar']), \
                    patch.object(sync, 'live_state', return_value=[]), \
                    patch.object(sync, 'read_credentials', side_effect=AssertionError('Windows secret read')), \
                    patch.object(sync, 'fetch_events', return_value=[]) as fetch, \
                    patch('builtins.print'):
                self.assertEqual(sync.main(), 0)
                self.assertEqual(fetch.call_args.args[3], 'fake-session')

    def test_live_sync_only_changes_owned_events_and_skips_unchanged(self):
        unchanged = sync.normalize_events([self.event()], sync.CALENDAR)[0]
        stale = unchanged | {'id': 'stale', 'externalId':'99'}
        other = unchanged | {'id': 'other', 'calendarId': 'other'}
        added = unchanged | {'id': 'new', 'title': 'New', 'externalId':'43'}
        with patch.object(sync, 'live_state', return_value=[unchanged, stale, other]), \
                patch.object(sync, 'local_request') as request:
            self.assertEqual(sync.save_events_live([unchanged, added], sync.CALENDAR), 2)
            self.assertEqual(request.call_args_list[0].args, ('events', added, 'POST'))
            self.assertEqual(request.call_args_list[1].args[0], 'events/stale')
            self.assertEqual(request.call_args_list[1].kwargs['method'], 'DELETE')
            self.assertEqual(request.call_args_list[2].args[0], 'timeTreeSync')
            self.assertEqual(request.call_count, 3)

    def test_live_failure_does_not_advance_sync_timestamp(self):
        event = sync.normalize_events([self.event()], sync.CALENDAR)[0]
        with patch.object(sync, 'live_state', return_value=[]), \
                patch.object(sync, 'local_request', side_effect=sync.SyncError('offline')) as request:
            with self.assertRaises(sync.SyncError):
                sync.save_events_live([event], sync.CALENDAR)
            self.assertEqual(request.call_count, 1)

    def test_browser_session_skips_password_login_and_scopes_cookie(self):
        jar = sync.http.cookiejar.CookieJar()
        with patch.object(sync.http.cookiejar, 'CookieJar', return_value=jar), \
                patch.object(sync.urllib.request, 'build_opener'), \
                patch.object(sync, 'request_json', side_effect=[
                    {'calendars': [{'id': 123, 'alias_code': sync.CALENDAR}]},
                    {'events': [], 'chunk': False}]) as request:
            self.assertEqual(sync.fetch_events('', '', sync.CALENDAR, 'fake-token'), [])
            self.assertEqual(request.call_count, 2)
            self.assertIn('/calendar/123/events/sync', request.call_args.args[1])
            cookie = next(iter(jar))
            self.assertEqual(cookie.domain, 'timetreeapp.com')
            self.assertTrue(cookie.secure)
            self.assertEqual(cookie.value, 'fake-token')

    def test_http_error_reports_stage_without_secret_body(self):
        opener = unittest.mock.Mock()
        opener.open.side_effect = sync.urllib.error.HTTPError(
            'https://timetreeapp.com/api/v1/auth/email/signin', 400, 'bad', {},
            io.BytesIO(b'{"code":-403,"password":"SECRET-PASSWORD"}'))
        with self.assertRaises(sync.SyncError) as caught:
            sync.request_json(opener, 'https://timetreeapp.com/api/v1/auth/email/signin')
        self.assertIn('Anmeldung: HTTP 400', str(caught.exception))
        self.assertIn('-403', str(caught.exception))
        self.assertNotIn('SECRET-PASSWORD', str(caught.exception))

    def event(self, **changes):
        event = {'id': 42, 'title': '<b>Termin</b>', 'start_at': 1792051200000,
                 'end_at': 1792054800000, 'all_day': False}
        return event | changes

    def test_normalization_deduplicates_and_ignores_deleted_events(self):
        events = sync.normalize_events([self.event(), self.event(title='Geändert'),
                                        self.event(id=43, deactivated_at=1)], sync.CALENDAR)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['title'], 'Geändert')
        self.assertTrue(events[0]['startAt'].endswith('+00:00'))
        self.assertEqual(events[0]['externalId'], '42')

    def test_invalid_time_aborts(self):
        with self.assertRaises(sync.SyncError):
            sync.normalize_events([self.event(start_at='bad')], sync.CALENDAR)

    def test_save_preserves_todos_and_other_calendars_and_is_repeatable(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / 'db.json'
            todos = [{'id': 'mine', 'title': 'Obst kaufen'}]
            other = {'id': 'other', 'source': 'timetree', 'calendarId': 'other'}
            stale = {'id': 'stale', 'source': 'timetree', 'calendarId': sync.CALENDAR}
            original = json.dumps({'todos': todos, 'events': [other, stale], '$schema': 'schema'}).encode()
            path.write_bytes(original)
            events = sync.normalize_events([self.event()], sync.CALENDAR)
            sync.save_events(path, events, sync.CALENDAR, original)
            self.assertEqual(path.with_name('db.json.before-timetree.bak').read_bytes(), original)
            sync.save_events(path, events, sync.CALENDAR, path.read_bytes())
            result = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(result['todos'], todos)
            self.assertEqual(result['events'], [other] + events)
            self.assertEqual(result['$schema'], 'schema')

    def test_concurrent_database_change_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / 'db.json'
            path.write_bytes(b'{"todos":[]}')
            original = path.read_bytes()
            path.write_bytes(b'{"todos":[{"title":"new"}]}')
            with self.assertRaises(sync.SyncError):
                sync.save_events(path, [], sync.CALENDAR, original)
            self.assertIn(b'new', path.read_bytes())

    def test_fetch_all_pages_and_reject_stalled_cursor(self):
        class Cookie:
            name = '_session_id'
        pages = [{'events': [self.event()], 'chunk': True, 'since': 10},
                 {'events': [self.event(title='Updated')], 'chunk': False}]
        with patch.object(sync.http.cookiejar, 'CookieJar', return_value=[Cookie()]), \
                patch.object(sync.urllib.request, 'build_opener'), \
                patch.object(sync, 'request_json', side_effect=[{},
                    {'calendars': [{'id': 123, 'alias_code': sync.CALENDAR}]}, *pages]) as request:
            events = sync.fetch_events('fake', 'fake', sync.CALENDAR)
            self.assertEqual(events[0]['title'], 'Updated')
            self.assertIn('since=10', request.call_args.args[1])
        with patch.object(sync.http.cookiejar, 'CookieJar', return_value=[Cookie()]), \
                patch.object(sync.urllib.request, 'build_opener'), \
                patch.object(sync, 'request_json', side_effect=[{},
                    {'calendars': [{'id': 123, 'alias_code': sync.CALENDAR}]},
                    {'events': [], 'chunk': True, 'since': 0},
                    {'events': [], 'chunk': True, 'since': 0}]):
            with self.assertRaises(sync.SyncError):
                sync.fetch_events('fake', 'fake', sync.CALENDAR)

    def test_string_cursor_is_encoded_and_initial_request_has_no_since(self):
        class Cookie:
            name = '_session_id'
        with patch.object(sync.http.cookiejar, 'CookieJar', return_value=[Cookie()]), \
                patch.object(sync.urllib.request, 'build_opener'), \
                patch.object(sync, 'request_json', side_effect=[{},
                    {'calendars': [{'id': 123, 'alias_code': sync.CALENDAR}]},
                    {'events': [self.event()], 'chunk': True, 'since': 'page+2/='},
                    {'events': [], 'chunk': False}]) as request:
            self.assertEqual(len(sync.fetch_events('fake', 'fake', sync.CALENDAR)), 1)
            self.assertTrue(request.call_args_list[2].args[1].endswith('/events/sync'))
            self.assertIn('since=page%2B2%2F%3D', request.call_args_list[3].args[1])


if __name__ == '__main__':
    unittest.main()
