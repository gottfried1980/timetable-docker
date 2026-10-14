#!/bin/sh
set -eu
node /app/init-db.mjs
exec node /app/display-server.mjs
