# Keep Node.js and Alpine versions explicit; the scheduled Trivy workflow scans
# this base and the built frontend image for new advisories.
FROM node:22.23.4-alpine3.24 AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci
FROM node:22.23.4-alpine3.24 AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public
RUN npm run build
FROM node:22.23.4-alpine3.24 AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN rm -rf /usr/local/lib/node_modules/npm \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx \
    && addgroup -S -g 10001 app \
    && adduser -S -u 10001 app -G app
COPY --from=build --chown=app:app /app/.next/standalone ./
COPY --from=build --chown=app:app /app/.next/static ./.next/static
COPY --from=build --chown=app:app /app/public ./public
COPY --chown=app:app entrypoint.mjs ./entrypoint.mjs
USER app
EXPOSE 3000
CMD ["node","entrypoint.mjs"]
