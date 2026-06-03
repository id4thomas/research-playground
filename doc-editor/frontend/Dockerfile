# --- build stage ---
FROM node:20-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
# npm install (not `npm ci`): lockfile은 플랫폼별 optional deps가 빠져있어
# ci가 sync 에러를 내므로 install로 해결.
RUN npm install

COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
