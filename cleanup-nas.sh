#!/bin/sh
# Removes only this Compose project's containers, network and local images.
# Its named database volume, media, keys and secret files are retained.
set -eu
expected='/volume1/docker/timetable-docker'
actual=$(pwd -P)
if [ "$actual" != "$expected" ]; then
    echo "Bitte zuerst: cd $expected" >&2
    exit 1
fi
if [ ! -f compose.yaml ]; then
    echo 'compose.yaml fehlt; nichts wurde entfernt.' >&2
    exit 1
fi
docker compose down --remove-orphans --rmi local
echo 'Projekt-Container und lokale Images entfernt. Datenbank-Volume erhalten.'
