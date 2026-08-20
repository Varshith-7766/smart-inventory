FROM python:3.11-slim

WORKDIR /app

# Backend
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY prediction/ /app/prediction/

# The app resolves frontend pages relative to the backend directory
# (backend/../frontend → /app/frontend), so everything is in place.

EXPOSE 5000

WORKDIR /app/backend

# Render injects a dynamic $PORT; fall back to 5000 for local docker runs.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 app:application"]