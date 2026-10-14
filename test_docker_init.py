"""Database initialization must preserve migrated user data and be repeatable."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parent


class DockerInitTests(unittest.TestCase):
    def test_initialization_and_migration(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            path = Path(folder) / 'db.json'
            env = os.environ | {'DB_PATH': str(path)}
            subprocess.run(['node', str(ROOT / 'docker/init-db.mjs')], env=env, check=True)
            self.assertEqual(json.loads(path.read_text()), {'todos': [], 'events': [], 'timeTreeSync': {}})
            todos = [{'id':'old', 'title':'Privat', 'dueDate':'2027-01-01'}]
            path.write_text(json.dumps({'todos': todos}), encoding='utf-8')
            subprocess.run(['node', str(ROOT / 'docker/init-db.mjs')], env=env, check=True)
            before = path.read_bytes()
            self.assertEqual(json.loads(before)['todos'], todos)
            subprocess.run(['node', str(ROOT / 'docker/init-db.mjs')], env=env, check=True)
            self.assertEqual(before, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
