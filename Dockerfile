# Image de production : l'interface Vue est construite, puis servie par Django avec l'API et les WebSockets.

FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENV=production \
    DATABASE_PATH=/app/data/db.sqlite3 \
    FRONTEND_DIST=/app/frontend/dist \
    PORT=10000
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN useradd --create-home joueur && mkdir -p /app/data && chown joueur /app/data
USER joueur
EXPOSE 10000
# La base SQLite est créée au démarrage. Daphne lit l'adresse du visiteur dans X-Forwarded-For.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec daphne --proxy-headers --bind 0.0.0.0 --port \"$PORT\" config.asgi:application"]
