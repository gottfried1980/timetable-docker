"""Local autoplay and photo slideshow checks without external media."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).parent
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    try:
        page=browser.new_page()
        page.add_init_script("""window.playAttempts=0;window.playerAllowed=false;
            Object.defineProperty(HTMLMediaElement.prototype,'paused',{get(){return this._paused!==false;}});
            HTMLMediaElement.prototype.play=function(){window.playAttempts++;if(!window.playerAllowed)return Promise.reject(new DOMException('blocked','NotAllowedError'));this._paused=false;this.dispatchEvent(new Event('play'));return Promise.resolve();};
            HTMLMediaElement.prototype.pause=function(){this._paused=true;this.dispatchEvent(new Event('pause'));};""")
        external=[]
        def route_request(route):
            url=route.request.url.split("?",1)[0]
            if not url.startswith('http://media.test/'): external.append(url)
            if url.endswith('.js'):
                route.fulfill(body=(root/url.rsplit('/',1)[1]).read_text(encoding='utf-8-sig'),content_type='text/javascript')
            elif url.endswith('media-list.json'):
                route.fulfill(body=json.dumps({'photos':[{'src':'media/photos/test.jpg','title':'Testfoto'}],'tracks':[{'src':'media/music/test.mp3','title':'Testmusik'}]}),content_type='application/json')
            elif url.endswith('/todos') or url.endswith('/events'):
                route.fulfill(body='[]',content_type='application/json')
            elif url.endswith('/timeTreeSync'):
                route.fulfill(body='{}',content_type='application/json')
            elif '/media/' in url: route.fulfill(status=200,body='')
            else:route.fulfill(body=(root/'index.html').read_text(encoding='utf-8'),content_type='text/html')
        page.route('**/*',route_request)
        page.goto('http://media.test/')
        page.get_by_text('Autoplay blockiert',exact=False).wait_for()
        assert page.locator('#familyMedia').is_visible()
        assert page.locator('#familyPhoto').get_attribute('src')=='media/photos/test.jpg'
        page.evaluate('playerAllowed=true')
        page.locator('#musicToggle').click()
        page.get_by_role('button',name='Musik pausieren',exact=True).wait_for()
        page.locator('#musicToggle').click()
        attempts=page.evaluate('playAttempts')
        page.keyboard.press('ArrowRight')
        assert page.evaluate('playAttempts')==attempts
        assert not external,external
        assert page.locator('iframe').count()==0
        print('Local player: autoplay fallback, pause, photos and no external requests passed')
    finally:browser.close()
