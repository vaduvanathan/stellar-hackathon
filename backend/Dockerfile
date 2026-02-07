# Walletsurance backend – Cloud Run
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# App code
COPY *.py ./
COPY templates/ templates/

# SQLite and env are provided at runtime (Cloud Run: env vars; DB in volume or /tmp)
ENV PORT=8080
EXPOSE 8080

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 60 app:app
