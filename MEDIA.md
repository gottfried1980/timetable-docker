# Optional local photos and music

This project ships without personal photos or music files. Add your own files
on your private NAS after installation:

```text
media/photos/    JPG, JPEG, PNG, WebP
media/music/     MP3, M4A, OGG, WAV
```

The Docker server discovers supported files directly in these folders. Reload
the dashboard after adding files. Subfolders and GIF/HEIC are not indexed.
No external video/music services are used.

Photos are displayed without cropping and rotate every 20 seconds. Slideshow
pause and next-photo controls are available. Local music attempts autoplay;
TV browsers may require one interaction before allowing audio. Start/pause and
volume controls are provided, and the playlist repeats.

Check the live index on the NAS:

```sh
curl -sS http://127.0.0.1:8080/media-list.json
sudo docker compose exec display ls -l /app/public/media/photos /app/public/media/music
```

Empty `photos`/`tracks` arrays mean that no supported files were found at the
mounted path. Files must be readable by UID 1000. NAS media ACLs are separate
from the stricter permissions required for keys and encrypted credentials.

For the Windows development server, run `python build-media.py` after adding
media; it generates a local index in `public`. This step is unnecessary on the
NAS. Keep personal media out of Git, release archives and public deployments.
See [INSTALL.md](INSTALL.md) for full instructions.
