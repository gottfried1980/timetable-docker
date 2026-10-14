"""Task CRUD browser checks against an in-memory fake API."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent


def main():
    tasks = [{'id': 'old', 'title': 'Vorhandene Aufgabe'}]
    fail_save = False
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))

            def route_request(route):
                url, method = route.request.url.split("?",1)[0], route.request.method
                headers = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': '*', 'Access-Control-Allow-Headers': '*'}
                if method == 'OPTIONS':
                    route.fulfill(status=204, headers=headers)
                    return
                if '/todos' in url:
                    requests.append(method)
                    if method in ('POST', 'PATCH') and fail_save:
                        route.fulfill(status=500, body='{}', headers=headers)
                        return
                    if method == 'POST':
                        saved = route.request.post_data_json | {'id': 'new'}
                        tasks.append(saved)
                    elif method == 'PATCH':
                        saved = next(task for task in tasks if task['id'] == url.rsplit('/', 1)[1])
                        saved.update(route.request.post_data_json)
                    elif method == 'DELETE':
                        tasks[:] = [task for task in tasks if task['id'] != url.rsplit('/', 1)[1]]
                        saved = {}
                    else:
                        saved = tasks
                    route.fulfill(body=json.dumps(saved), content_type='application/json', headers=headers)
                elif url.endswith('/events'):
                    route.fulfill(body='[]', content_type='application/json', headers=headers)
                elif url.endswith('/timeTreeSync'):
                    route.fulfill(body='{}', content_type='application/json', headers=headers)
                elif url.endswith('.js'):
                    route.fulfill(body=(ROOT / url.rsplit('/', 1)[1]).read_text(encoding='utf-8-sig'), content_type='text/javascript')
                else:
                    route.fulfill(body=(ROOT / 'index.html').read_text(encoding='utf-8'), content_type='text/html')

            page.route('**/*', route_request)
            page.goto('http://tasks.test/')
            page.locator('#toggleTasks').click()
            page.locator('.todo-title').wait_for()
            page.locator('#todoinput').fill('<b>Neue Aufgabe</b>')
            page.locator('#todoDueDate').fill('2026-01-01')
            page.locator('#addButton').click()
            page.get_by_text('<b>Neue Aufgabe</b>', exact=True).wait_for()
            assert tasks[-1]['dueDate'] == '2026-01-01'
            assert page.locator('.todo-due.overdue').count() == 1
            page.get_by_role('button', name='Aufgabe bearbeiten: <b>Neue Aufgabe</b>', exact=True).click()
            page.locator('#todoinput').fill('Bearbeitet')
            page.locator('#todoDueDate').fill('2027-04-05')
            fail_save = True
            page.locator('#addButton').click()
            page.get_by_text('Die Aufgabe konnte nicht gespeichert werden.', exact=False).wait_for()
            assert page.locator('#todoinput').input_value() == 'Bearbeitet'
            assert tasks[-1]['title'] == '<b>Neue Aufgabe</b>'
            fail_save = False
            page.locator('#addButton').click()
            page.get_by_text('Bearbeitet', exact=True).wait_for()
            assert tasks[-1]['dueDate'] == '2027-04-05'
            page.get_by_role('button', name='Aufgabe bearbeiten: Bearbeitet', exact=True).click()
            page.locator('#todoDueDate').fill('')
            page.locator('#addButton').click()
            page.locator('#cancelEdit').wait_for(state='hidden')
            assert tasks[-1]['dueDate'] is None
            page.get_by_role('button', name='Aufgabe löschen: Bearbeitet', exact=True).click()
            page.get_by_role('button', name='Löschen bestätigen', exact=True).click()
            page.get_by_text('Bearbeitet', exact=True).wait_for(state='detached')
            assert len(tasks) == 1 and tasks[0]['id'] == 'old'
            assert 'POST' in requests and 'PATCH' in requests and 'DELETE' in requests
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            print('Tasks: create, edit, due date, remove date, delete, save failure and mobile layout passed')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
