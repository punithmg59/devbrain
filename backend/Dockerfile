FROM python:3.12-slim

# Install system dependencies.
# ca-certificates is REQUIRED: python:3.12-slim ships with an incomplete CA
# bundle. Without it, ssl.create_default_context() cannot verify Supabase's
# certificate chain, causing CERTIFICATE_VERIFY_FAILED in production.
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"