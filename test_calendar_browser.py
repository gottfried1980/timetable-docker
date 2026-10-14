"""Browser integration checks with synthetic events; no private data or network."""
from datetime import datetime, timezone
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.clock.install(time=datetime(2026, 10, 14, 8, tzinfo=timezone.utc))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            events = [{'id': 'test', 'source': 'timetree', 'calendarId': 'demo-calendar',
                       'title': '<b>Besprechung</b>', 'startAt': '2026-10-14T11:00:00+02:00',
                       'endAt': '2026-10-14T12:00:00+02:00', 'recurrences': ['FREQ=WEEKLY']}]

            def route_request(route):
                url = route.request.url.split("?",1)[0]
                if url.endswith('/calendar.js') or url.endswith('/tasks.js') or url.endswith('/media.js'):
                    route.fulfill(body=(ROOT / url.rsplit('/', 1)[1]).read_text(encoding='utf-8-sig'), content_type='text/javascript')
                elif url.endswith('/events'):
                    route.fulfill(body=json.dumps(events), content_type='application/json', headers={'Access-Control-Allow-Origin': '*'})
                elif url.endswith('/todos'):
                    route.fulfill(body='[]', content_type='application/json', headers={'Access-Control-Allow-Origin': '*'})
                elif url.endswith('/timeTreeSync'):
                    route.fulfill(body='{"lastSyncedAt":"2026-10-14T07:00:00Z"}', content_type='application/json', headers={'Access-Control-Allow-Origin': '*'})
                else:
                    route.fulfill(body=(ROOT / 'index.html').read_text(encoding='utf-8'), content_type='text/html')

            page.route('**/*', route_request)
            page.goto('http://calendar.test/')
            page.locator('.agenda-entry').wait_for()
            before = page.locator('#clock').inner_text()
            page.clock.run_for(1000)
            assert page.locator('#clock').inner_text() != before
            assert page.locator('#dayView').get_attribute('aria-pressed') == 'true'
            assert page.locator('.agenda-entry strong').inner_text() == '<b>Besprechung</b>'
            assert page.locator('.agenda-entry.recurring-event').count() == 1
            assert not page.locator('#eventReminder').is_visible()
            assert page.locator('#yearGrid .month').count() == 12
            assert page.locator('.calendar-date').count() == 365
            assert page.locator('.calendar-date.holiday').count() == 13
            assert page.locator('#autoView').is_checked()
            assert not page.locator('#tasksPanel').is_visible()
            assert not page.locator('#yearPanel').is_visible()
            assert 'Als Nächstes' in page.locator('#nextAppointment').inner_text()
            page.clock.run_for(60001)
            assert page.locator('.week-day').count() == 7
            page.clock.run_for(60001)
            assert page.locator('#dayView').get_attribute('aria-pressed') == 'true'
            page.locator('#weekView').click()
            page.locator('#toggleYear').click()
            page.get_by_role('button', name='26. Oktober 2026 · Nationalfeiertag', exact=True).click()
            assert not page.locator('#autoView').is_checked()
            assert page.locator('#selectedDate').input_value() == '2026-10-26'
            assert page.locator('.holiday-banner').inner_text() == 'Nationalfeiertag'
            page.clock.run_for(180001)
            assert page.locator('#dayView').get_attribute('aria-pressed') == 'true'
            page.locator('#goToday').click()
            assert page.locator('#selectedDate').input_value() == '2026-10-14'
            assert not page.locator('#autoView').is_checked()
            page.locator('#nextYear').click()
            assert page.locator('#yearHeading').inner_text() == '2027'
            assert page.locator('.calendar-date').count() == 365
            page.locator('#nextYear').click()
            assert page.locator('#yearHeading').inner_text() == '2028'
            assert page.locator('.calendar-date').count() == 366
            assert page.locator('.calendar-date.holiday').count() == 13
            page.clock.set_system_time(datetime(2026, 10, 14, 8, 29, 45, tzinfo=timezone.utc))
            page.clock.run_for(31000)
            assert page.locator('#eventReminder').is_visible(), page.evaluate('({now: new Date().toISOString(), storage: sessionStorage.getItem("timetree-reminders-v1"), text: document.getElementById("reminderItems").textContent})')
            assert page.locator('#reminderItems .recurring-event').count() == 1
            assert 'In 30 Minuten' in page.locator('#reminderItems').inner_text()
            page.clock.run_for(20001)
            assert not page.locator('#eventReminder').is_visible()
            page.reload()
            page.locator('.agenda-entry').wait_for()
            assert not page.locator('#eventReminder').is_visible()
            page.set_viewport_size({'width': 390, 'height': 844})
            for number in range(12):
                events.append({'id': 'dense-' + str(number), 'source': 'timetree',
                               'calendarId': 'demo-calendar', 'title': 'Käsemarkt Maria Taferl ' + str(number),
                               'startAt': '2026-10-13T12:00:00+02:00',
                               'endAt': '2026-10-15T12:00:00+02:00'})
            page.reload()
            page.locator('.dense-agenda').wait_for()
            assert page.locator('.agenda-entry').count() == 13
            label = page.locator('.time-label').first
            assert label.inner_text() == 'Fortlaufend'
            assert label.evaluate('(el) => getComputedStyle(el).whiteSpace') == 'nowrap'
            assert label.evaluate('(el) => el.scrollWidth <= el.clientWidth')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            assert page.locator('.dense-agenda .agenda-list').evaluate('(el) => getComputedStyle(el).columnCount') == '2'
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(ROOT / 'calendar-mobile.png'), full_page=True)
            assert not errors, errors
            print('Browser: views, future years, recurring colors, reminder timing/deduplication and mobile layout passed')
        finally:
            browser.close()


if __name__ == '__main__':
    main()

