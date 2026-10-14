"""Live media endpoint must override an old empty static file."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import patch
import timetree_sync as sync

ROOT=Path(__file__).parent.resolve()


class MediaServerTests(unittest.TestCase):
    def test_live_list_ignores_stale_file_and_detects_new_files(self):
        binary=Path(os.environ['APPDATA'])/'npm/node_modules/json-server/lib/bin.js'
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app=Path(folder); public=app/'public'; photos=public/'media/photos'; music=public/'media/music'
            photos.mkdir(parents=True); music.mkdir()
            (photos/'Familie.JPG').write_bytes(b'test')
            (music/'Mein Lied.mp3').write_bytes(b'test music')
            (public/'media-list.json').write_text('{"photos":[],"tracks":[]}')
            (public/'version.json').write_text('{"release":"test"}')
            (public/'index.html').write_text('<html>Tagesdisplay</html>')
            db=app/'db.json'; db.write_text('{"todos":[],"events":[],"timeTreeSync":{}}')
            ports=[]
            for _ in range(2):
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1',0));ports.append(sock.getsockname()[1])
            env=os.environ|{'APP_DIRECTORY':str(app),'DB_PATH':str(db),'PORT':str(ports[0]),'JSON_SERVER_INTERNAL_PORT':str(ports[1]),'JSON_SERVER_BIN':str(binary)}
            process=subprocess.Popen(['node',str(ROOT/'docker/display-server.mjs')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            base='http://127.0.0.1:'+str(ports[0])
            try:
                for _ in range(60):
                    try:
                        with urllib.request.urlopen(base+'/version.json',timeout=1) as response:
                            if response.status==200:break
                    except OSError:time.sleep(0.1)
                with urllib.request.urlopen(base+'/media-list.json') as response:
                    data=json.load(response)
                    self.assertEqual(response.headers['X-Timetable-Media'],'live-v3')
                    self.assertEqual(response.headers['Cache-Control'],'no-store')
                request=urllib.request.Request(base+'/',headers={'If-None-Match':'old-cache'})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status,200)
                    self.assertIn('no-store',response.headers['Cache-Control'])
                    self.assertIn(b'Tagesdisplay',response.read())
                self.assertEqual(len(data['photos']),1)
                self.assertEqual(len(data['tracks']),1)
                self.assertIn('Mein%20Lied.mp3',data['tracks'][0]['src'])
                (photos/'neu.png').write_bytes(b'new photo')
                with urllib.request.urlopen(base+'/api/media') as response:
                    self.assertEqual(len(json.load(response)['photos']),2)
                with urllib.request.urlopen(base+'/'+data['tracks'][0]['src']) as response:
                    self.assertEqual(response.read(),b'test music')
                request=urllib.request.Request(base+'/todos',data=b'{"title":"test"}',headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(json.load(response)['title'],'test')
                raw={'id':42,'title':'Westbahnhof fahren','start_at':1792051200000,'end_at':1792054800000}
                event=sync.normalize_events([raw],sync.CALENDAR)[0]
                with patch.dict(os.environ,{'JSON_SERVER_URL':base}):
                    self.assertEqual(sync.save_events_live([event],sync.CALENDAR),1)
                    stored=sync.local_request('events')
                    self.assertNotEqual(stored[0]['id'],event['id'])
                    self.assertEqual(sync.save_events_live([event],sync.CALENDAR),0)
                    sync.local_request('events',event,'POST')
                    self.assertEqual(len(sync.local_request('events')),2)
                    self.assertEqual(sync.save_events_live([event],sync.CALENDAR),1)
                    self.assertEqual(len(sync.local_request('events')),1)
                    self.assertEqual(sync.local_request('todos')[0]['title'],'test')
            finally:
                if os.name=='nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else:process.terminate()
                process.wait(timeout=10)


if __name__=='__main__':unittest.main()
