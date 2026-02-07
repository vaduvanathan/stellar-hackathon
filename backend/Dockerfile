# Walletsurance backend – Cloud Run
#
# IMPORTANT: Build with context = backend/ so key_encrypt.py and other .py files are included:
#   docker build -t walletsurance-backend -f backend/Dockerfile backend/
# From repo root, or:  cd backend && docker build -t walletsurance-backend .
#
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# App code – all .py files (key_encrypt, horizon_client, sms_client, etc.) must be in build context
COPY app.py config.py key_encrypt.py horizon_client.py sms_client.py build_deposit.py onmeta_client.py soroban_client.py ./
COPY templates/ templates/

# SQLite and env are provided at runtime (Cloud Run: env vars; DB in volume or /tmp)
ENV PORT=8080
EXPOSE 8080

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 60 app:app
