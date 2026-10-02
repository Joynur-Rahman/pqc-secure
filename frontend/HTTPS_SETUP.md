# HTTPS Configuration for Local Development

This guide explains how to set up HTTPS for local development of the PQC-Secure frontend.

## Overview

For secure development and testing of authentication features, the frontend supports HTTPS using self-signed SSL certificates. This document explains how to enable and use HTTPS locally.

## Prerequisites

- OpenSSL installed on your system
  - **macOS**: `brew install openssl`
  - **Ubuntu/Debian**: `sudo apt-get install openssl`
  - **Windows**: Use Git Bash, WSL, or install OpenSSL manually
  - **Docker**: Built-in to all containers

## Quick Start

### Option 1: Automatic Certificate Generation (Recommended)

```bash
cd frontend
npm run dev:https
```

This command:
1. Automatically checks for SSL certificates
2. Generates self-signed certificates if missing
3. Starts the Vite dev server with HTTPS enabled on `https://localhost:3000`

### Option 2: Manual Certificate Generation

Generate certificates manually:

```bash
# From the frontend directory
node scripts/check-certs.mjs
```

Or using the shell script:

```bash
# From project root
chmod +x scripts/generate-certs.sh
./scripts/generate-certs.sh
```

Then start development:

```bash
cd frontend
VITE_USE_HTTPS=true npm run dev
```

## Configuration

### Environment Variables

**Default (.env)**
```
VITE_USE_HTTPS=false          # HTTPS disabled (HTTP on port 3000)
VITE_API_TARGET=http://localhost:8000
VITE_API_URL=http://localhost:8000/api
```

**HTTPS Mode (.env.https)**
```
VITE_USE_HTTPS=true           # HTTPS enabled (HTTPS on port 3000)
VITE_API_TARGET=http://localhost:8000
VITE_API_URL=https://localhost:3000/api
```

### Using Environment Files

```bash
# Use HTTP (default)
npm run dev

# Use HTTPS
npm run dev:https

# Or manually set environment variable
VITE_USE_HTTPS=true npm run dev
```

## Certificate Details

### Certificate Location
```
frontend/certs/
├── server.key  (private key)
└── server.crt  (self-signed certificate)
```

### Certificate Properties
- **Algorithm**: RSA-4096
- **Validity**: 365 days from generation
- **Subject**: CN=localhost
- **Self-signed**: Yes (for local development only)

### Regenerating Certificates

To regenerate certificates (e.g., after expiration):

```bash
rm -rf frontend/certs/
npm run dev:https  # Certificates will be auto-generated
```

## Browser Warnings

When accessing `https://localhost:3000`, you'll see a browser security warning because:

1. The certificate is self-signed (not issued by a trusted CA)
2. It's only valid for local development
3. The certificate is only trusted for `localhost`

**This is expected and normal for local development.**

### Accepting the Certificate

**Chrome/Edge**:
1. Click "Advanced"
2. Click "Proceed to localhost"

**Firefox**:
1. Click "Advanced..."
2. Click "Accept the Risk and Continue"

**Safari**:
1. Click "Show Details"
2. Click "visit this website"

## API Proxy Configuration

The dev server proxies `/api` requests to the backend:

```
Browser Request: https://localhost:3000/api/auth/login
    ↓
Vite Proxy: http://localhost:8000/api/auth/login
```

Key settings:
- **Target**: Configurable via `VITE_API_TARGET`
- **changeOrigin**: `true` (modifies Host header)
- **secure**: `false` (accepts self-signed backend certificates if needed)

## Testing Secure Features

### Testing Authentication with HTTPS

```bash
# Start backend
docker-compose up -d

# Start frontend with HTTPS
npm run dev:https
```

Then:
1. Open browser to `https://localhost:3000`
2. Accept security warning
3. Register and login (cookies will be set securely)
4. Verify session works across page reloads

### Testing Session Cookies

With HTTPS enabled, session cookies include:
- `Secure` flag (only transmitted over HTTPS)
- `HttpOnly` flag (not accessible to JavaScript)
- `SameSite=Strict` (CSRF protection)

### Testing Mixed Content

The browser will block non-HTTPS resources loaded on HTTPS pages:

```
✓ Allowed:  https://localhost:3000 → https://localhost:3001/api
✓ Allowed:  https://localhost:3000 → http://localhost:3000/api (same origin)
✗ Blocked:  https://localhost:3000 → http://localhost:8001/external
```

## Development Workflow

### For HTTP Development (Default)

```bash
cd frontend
npm run dev
# Server runs on http://localhost:3000
```

### For HTTPS Development

```bash
cd frontend
npm run dev:https
# Server runs on https://localhost:3000
# Certificates auto-generated if missing
```

### Switching Between HTTP and HTTPS

```bash
# Stop current server (Ctrl+C)
npm run dev      # Switch to HTTP
npm run dev:https # Switch to HTTPS
```

## Troubleshooting

### "Cannot find module 'fs'" Error

The certificate check script uses Node.js built-ins. Ensure you're running it with Node:

```bash
# ✓ Correct
node scripts/check-certs.mjs

# ✗ Wrong
bash scripts/check-certs.mjs
```

### "openssl: command not found"

Install OpenSSL:

```bash
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt-get install openssl

# Windows (using WSL or Git Bash)
sudo apt-get install openssl
```

### Certificates Not Found After Running dev:https

1. Verify script execution succeeded (check for "✓" message)
2. Check that `frontend/certs/` directory exists
3. Manually run: `node scripts/check-certs.mjs`
4. Check file permissions: `ls -la frontend/certs/`

### Port 3000 Already in Use

```bash
# Find process using port 3000
lsof -i :3000  # macOS/Linux

# Kill process (if safe)
kill -9 <PID>

# Or use a different port
VITE_PORT=3001 npm run dev
```

### HTTPS Connection Fails in Production

Production deployment should use:
1. Real certificates from a trusted CA (Let's Encrypt, etc.)
2. Reverse proxy (nginx, HAProxy) with TLS termination
3. Backend over HTTPS if needed

See `DOCKER_SETUP.md` for production recommendations.

## Security Considerations

### For Development Only
- Self-signed certificates are suitable for local development only
- Never use these certificates in production
- These certificates are not trusted by any browser by default

### For Production
- Use certificates from a trusted Certificate Authority (Let's Encrypt, DigiCert, etc.)
- Implement HSTS (HTTP Strict-Transport-Security)
- Use a reverse proxy for TLS termination
- Keep certificates and keys secure

### Environment Variables
- Never commit `.env` files with secrets
- `.env.https` can be committed (no secrets, only local configuration)
- Use `.env.local` for machine-specific overrides

## References

- [Vite HTTPS Configuration](https://vitejs.dev/config/server-options.html#server-https)
- [Node.js HTTPS Module](https://nodejs.org/api/https.html)
- [Self-Signed Certificates (OpenSSL)](https://www.openssl.org/docs/man1.1.1/man1/req.html)
- [Browser Security Warnings](https://support.mozilla.org/kb/warning-unverified-connection)

## FAQ

**Q: Can I use HTTPS in production with these certificates?**
A: No. Always use certificates from a trusted Certificate Authority.

**Q: Why is the certificate invalid?**
A: It's self-signed, so browsers don't recognize the issuer. This is expected for local development.

**Q: Can I share these certificates with my team?**
A: You can, but each developer should generate their own certificates locally for security.

**Q: How do I disable the certificate warning?**
A: You can't permanently disable it in browsers (for security). You can click "Advanced" and "Proceed to localhost" each time, or use incognito mode.

**Q: What if I need HTTPS on a different port?**
A: Edit `frontend/vite.config.ts` and change the `port` value, then regenerate certificates for that hostname.
