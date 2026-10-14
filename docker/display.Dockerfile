FROM node:22-alpine
WORKDIR /app
COPY docker/package.json docker/package-lock.json ./
RUN npm ci --omit=dev && mkdir /data && chown node:node /data
COPY index.html calendar.js tasks.js media.js version.json ./public/
COPY docker/init-db.mjs ./
COPY docker/media-index.mjs docker/display-server.mjs ./
COPY docker/display-entrypoint.sh ./
COPY release-manifest.json ./
COPY docker/verify-display.mjs ./
RUN node /app/verify-display.mjs
USER node
EXPOSE 3000
ENTRYPOINT ["sh", "/app/display-entrypoint.sh"]
