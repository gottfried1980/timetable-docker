# Timetable Display

A home calendar dashboard for a TV, kiosk computer or Raspberry Pi browser.
The NAS runs the application; the display device only needs a browser.

Features include a daily agenda, weekly view, an Austrian yearly calendar,
editable tasks with due dates, optional personal photo slideshows, a local
music player and reminders before upcoming appointments.

## Installation

See **[INSTALL.md](INSTALL.md)** for the complete installation guide, including
encrypted TimeTree credentials, Docker Compose, updates, backups and diagnostics.

- [Media setup](MEDIA.md)
- [Docker architecture](DOCKER.md)
- [NAS quick start](NAS-START.md)
- [Windows setup](TIMETREE.md)

## Privacy and limitations

No personal photos, music, database, passwords or encryption keys are included
in the distribution. Add your own media after installation. Keep keys, session
files and backups outside Git.

TimeTree's official API has been discontinued. This project uses its unofficial
web interface and a browser session cookie; upstream changes may break access.
Sessions expire and require manual renewal. Recurring events currently display
their original stored occurrence, rather than an expanded recurrence schedule.

The dashboard has no built-in authentication. Use it on a trusted local network
or behind an authenticated reverse proxy/VPN. Docker secrets provide file
mounts; the session is encrypted by this project before it is mounted.
Administrators with access to both the key and ciphertext can decrypt it.

The current interface uses German labels and Austrian dates. The installation
and operating documentation is in English.
