# Timetable Display

A home calendar dashboard for a TV, kiosk computer or Raspberry Pi browser.
The NAS runs the application; the display device only needs a browser.

## What is this for?

This project turns a spare screen into an always-on family wall calendar.

The typical situation: the family shares a TimeTree calendar on their phones,
but at home nobody looks at it, appointments get missed, and the paper
calendar in the kitchen is always out of date. At the same time a NAS is
already running around the clock, and an old TV, monitor or Raspberry Pi is
gathering dust.

With this project:

- The NAS imports the shared TimeTree calendar automatically every 15 minutes.
- A TV or kiosk screen shows today's agenda, the week ahead and the whole year
  at a glance, without anyone having to touch it.
- Reminders pop up on the screen before an appointment starts.
- Household tasks with due dates can be added and ticked off directly on the
  screen.
- Optionally the screen doubles as a digital photo frame and plays local music.

Everything stays on your home network. There is no cloud service, no account
with a third-party dashboard provider, and no personal data leaves the NAS.

Use it if you want one central, always visible overview of the household's
appointments and tasks. It is not meant for public internet access, multi-user
cloud scenarios or installations without a NAS/server of your own.

## Features

Daily agenda, weekly view, an Austrian yearly calendar, editable tasks with
due dates, optional personal photo slideshows, a local music player and
reminders before upcoming appointments.

## Sync interval

The `sync` container imports the TimeTree calendar once at startup and then
every 15 minutes (`SYNC_INTERVAL_SECONDS=900` in `compose.yaml`, minimum 60).
A single run is aborted after 10 minutes; if it fails, the last successful
state stays visible and the next interval retries. The Windows scheduled task
uses the same 15-minute rhythm. To change it, set the variable in `.env` or
`compose.yaml`, for example:

```yaml
SYNC_INTERVAL_SECONDS: "300"   # every 5 minutes
```

Keep in mind that every run uses the unofficial TimeTree web interface with a
session cookie, so very short intervals increase the risk of the session being
invalidated.

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

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
