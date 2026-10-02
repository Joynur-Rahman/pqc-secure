# HTTPS Configuration for Local Development

## Summary

This document describes the HTTPS setup configured for local development of the PQC-Secure application, enabling secure testing of authentication features and SSL/TLS functionality.

## What Was Configured

### 1. Self-Signed Certificate Generation

- **Location**: `scripts/generate-certs.sh` (bash) and `frontend/scripts/check-certs.mjs` (Node.js)
- **Purpose**: Generate self-signed SSL certificates for local development
- **Certificate Details**:
  - Algorithm: RSA-4096
  - Validity: 365 days
  - Subject: CN=localhost
  - Location: `frontend/certs/`

### 2. Vite Configuration

**File**: `frontend/vite.config.ts`

- Added conditional HTTPS support based on `VITE_USE_HTTPS` environment variable
- When HTTPS is enabled:
  - Reads certificates from `frontend/certs/server.key` and `frontend/certs/server.crt`
  - Starts dev server on `https://localhost:3000`
  - Maintains proxy to backend at `http://localhost:8000`

### 3. Environment Configuration

**Files**:
- `frontend/.env` (default HTTP configuration)
- `frontend/.env.https` (HTTPS configuration)

**Variables**:
- `VITE_USE_HTTPS`: Enable/disable HTTPS (true/false)
- `VITE_API_TARGET`: Backend API target URL
- `VITE_API_URL`: Frontend-visible API URL

### 4. NPM Scripts

**File**: `frontend/package.json`

Added new script:
```bash
npm run dev:https
```

This script:
1. Automatically checks for SSL certificates
2. Generates self-signed certificates if missing
3. Starts Vite dev server with HTTPS enabled

### 5. Certificate Auto-Generation

**File**: `frontend/scripts/check-certs.mjs`

- Automatically runs before HTTPS dev server starts
- Checks if certificates exist
- Generates certificates if missing
- Provides helpful error messages if OpenSSL is not installed

### 6. Documentation

- `frontend/HTTPS_SETUP.md`: Comprehensive HTTPS setup guide
- `frontend/BUILD_TOOLING.md`: Updated with HTTPS instructions
- `.gitignore`: Excludes certificates from version control

## How to Use

### Start with HTTPS

```bash
cd frontend
npm run dev:https
```

The server will:
1. Auto-generate certificates if missing (using OpenSSL)
2. Start on `https://localhost:3000`
3. Show a browser security warning (expected for self-signed certs)
4. Accept the warning to proceed

### Start with HTTP (Default)

```bash
cd frontend
npm run dev
```

### Switch Between HTTP and HTTPS

Simply stop the server and start with the desired command:
```bash
# Stop current server (Ctrl+C)
npm run dev       # HTTP
npm run dev:https # HTTPS
```

## Browser Security Warnings

When accessing `https://localhost:3000`, browsers will show a security warning because:
1. The certificate is self-signed (not from a trusted CA)
2. It's for local development only
3. This is expected and normal

### Accepting the Warning

- **Chrome/Edge**: Click "Advanced" → "Proceed to localhost"
- **Firefox**: Click "Advanced..." → "Accept the Risk and Continue"
- **Safari**: Click "Show Details" → "visit this website"

## Requirements

### For HTTPS Development
- OpenSSL must be installed
  - **macOS**: `brew install openssl`
  - **Ubuntu/Debian**: `sudo apt-get install openssl`
  - **Windows**: Use WSL or Git Bash

### For HTTP Development (Default)
- No additional requirements

## Certificate Details

### Location
```
frontend/certs/
├── server.key    (RSA private key, 4096-bit)
└── server.crt    (Self-signed certificate)
```

### Regenerating Certificates
```bash
# Delete existing certificates
rm -rf frontend/certs/

# Restart HTTPS dev server - certificates will be auto-generated
npm run dev:https
```

## API Proxy Configuration

The dev server maintains API proxying whether using HTTP or HTTPS:

```
https://localhost:3000 → (proxy) → http://localhost:8000
```

Key settings:
- **Target**: `http://localhost:8000` (configurable via `VITE_API_TARGET`)
- **changeOrigin**: `true`
- **secure**: `false` (accepts self-signed certs from backend if needed)

## Security Notes

### For Local Development
- Self-signed certificates are suitable for local development only
- Certificates are excluded from version control (`.gitignore`)
- Each developer generates their own local certificates

### For Production
- **Never** use self-signed certificates in production
- Use certificates from a trusted CA (Let's Encrypt, DigiCert, etc.)
- Deploy behind a reverse proxy (nginx, HAProxy) with TLS termination
- Implement HSTS (HTTP Strict-Transport-Security)

## Troubleshooting

### HTTPS Dev Server Fails to Start

1. Check OpenSSL is installed:
   ```bash
   openssl version
   ```
   If not installed, install via your package manager

2. Manually generate certificates:
   ```bash
   node frontend/scripts/check-certs.mjs
   ```

3. Check certificate directory exists:
   ```bash
   ls -la frontend/certs/
   ```

### Port 3000 Already in Use

```bash
# Find process using port 3000
lsof -i :3000

# Kill process (if safe) or use different port
PORT=3001 npm run dev:https
```

### Browser Still Shows Warning After Accepting

- Browser security cache: Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)
- Private/Incognito mode: Open URL in new incognito window

### API Calls Fail Over HTTPS

1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check `VITE_API_TARGET` environment variable:
   ```bash
   echo $VITE_API_TARGET
   ```

3. Verify API URL in browser console

## Files Modified/Created

### New Files
- `scripts/generate-certs.sh` - Bash script for certificate generation
- `frontend/scripts/check-certs.mjs` - Node.js certificate check/generation script
- `frontend/.env.https` - HTTPS environment configuration
- `frontend/HTTPS_SETUP.md` - Detailed HTTPS setup guide
- `.kiro/HTTPS_LOCAL_DEVELOPMENT.md` - This file

### Modified Files
- `frontend/vite.config.ts` - Added HTTPS support
- `frontend/package.json` - Added `dev:https` script
- `frontend/.env` - Added HTTPS-related variables
- `frontend/.gitignore` - Excluded certificate files
- `frontend/BUILD_TOOLING.md` - Updated with HTTPS instructions

## Next Steps

1. Install dependencies:
   ```bash
   cd frontend && npm install
   ```

2. Start HTTPS dev server:
   ```bash
   npm run dev:https
   ```

3. Open browser and accept certificate warning

4. For detailed HTTPS configuration options, see `frontend/HTTPS_SETUP.md`

## Related Documentation

- `frontend/HTTPS_SETUP.md` - Comprehensive HTTPS setup and troubleshooting guide
- `frontend/BUILD_TOOLING.md` - Overall frontend build tooling documentation
- `DOCKER_SETUP.md` - Docker Compose configuration for all services
- `QUICKSTART.md` - Quick start guide for the entire project
