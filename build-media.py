"""Index local media for both the NAS and Windows webserver."""
import json
from pathlib import Path
import shutil
from urllib.parse import quote

root = Path(__file__).resolve().parent
media = root / 'media'
for folder in ('photos', 'music'):
    (media / folder).mkdir(parents=True, exist_ok=True)

def entries(folder, extensions):
    return [{'src':'media/' + folder + '/' + quote(path.name), 'title':path.stem}
            for path in sorted((media / folder).iterdir()) if path.is_file() and path.suffix.lower() in extensions]

data = {'photos': entries('photos', {'.jpg','.jpeg','.png','.webp'}),
        'tracks': entries('music', {'.mp3','.m4a','.ogg','.wav'})}
(media / 'manifest.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
shutil.copytree(media, root / 'public/media', dirs_exist_ok=True)
print(f"Medien bereit: {len(data['photos'])} Fotos, {len(data['tracks'])} Musikstücke.")

(root / 'public/media-list.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
