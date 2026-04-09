# Backend image
# Build context: proposal-pilot/ (project root)

FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ backend/

# DB lives in a mounted volume at /app/proposalpilot.db
# DB_PATH defaults to "proposalpilot.db" which resolves to /app/proposalpilot.db

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
