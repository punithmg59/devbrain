# Supabase CA Certificate

This directory stores the Supabase root CA certificate used for SSL verification
in production (Railway deployment).

## How to obtain the certificate

1. Open the Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **Project Settings** -> **Database** -> **SSL Configuration**
4. Download the **Server CA certificate** (.crt or .cer file)
5. Convert to PEM format if needed:
   `openssl x509 -in supabase-ca.cer -out prod-ca-cert.pem -outform PEM`
6. Place the file at `backend/certs/prod-ca-cert.pem`

## Railway deployment options

### Option A: File path (recommended for Docker deployments)
- Include the certs/prod-ca-cert.pem file in your repository (it is a public CA cert, not a secret)
- Set Railway environment variable:
  DATABASE_SSL_CA_CERT_PATH=/app/certs/prod-ca-cert.pem

### Option B: Inline environment variable (no file needed)
- Copy the PEM content from the certificate file
- Set Railway environment variable DATABASE_SSL_CA_CERT to the full PEM string
- Replace real newlines with \n in the Railway UI if needed
- The application automatically normalises \n -> real newlines

## Security note
The Supabase CA certificate is a public root certificate.
It is safe to commit to source control (it contains no private keys).
