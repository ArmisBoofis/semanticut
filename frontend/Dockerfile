# Story 1.3: Next.js dev server with hot reload when source is bind-mounted.
# Production: run `npm run build` + `npm run start` (not the default Compose path yet).
FROM node:22-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

EXPOSE 3000
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
