# ==============================================================================
# KHOJAI Frontend - Production Dockerfile (Vite + React 19 + Nginx)
# ==============================================================================

# Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

# Enable corepack for pnpm
RUN corepack enable && corepack prepare pnpm@10.4.1 --activate

# Copy dependency manifests
COPY package.json pnpm-lock.yaml ./
COPY patches ./patches

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source files
COPY client ./client
COPY shared ./shared
COPY tsconfig.json tsconfig.node.json vite.config.ts components.json ./

# Build production bundle
ENV NODE_ENV=production
RUN pnpm run build

# Production Serving Stage (Nginx)
FROM nginx:alpine AS runner

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration with reverse proxy for /api
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets from build stage
COPY --from=builder /app/dist/public /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
