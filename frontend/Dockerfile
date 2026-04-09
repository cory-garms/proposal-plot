# Frontend image — two-stage build
# Stage 1: build the Vite app
# Stage 2: serve with nginx, proxy /api/* to backend

# ---- build ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# In Docker, the frontend always talks to nginx which proxies /api -> backend.
# VITE_API_BASE_URL=/api is baked into the JS bundle at build time.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- serve ----
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
