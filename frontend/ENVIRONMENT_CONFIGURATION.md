# Frontend Environment Configuration Guide

This document explains how to configure the PQC-Secure frontend for different deployment scenarios.

## Overview

The frontend uses Vite's environment variables to configure API endpoints, HTTPS settings, and other runtime options. Environment variables are prefixed with `VITE_` to ensure they are exposed to the browser at build time.

## Environment Files

Vite automatically loads environment variables from `.env` files based on the mode:

- `.env` - Loaded in all cases (default, checked in)
- `.env.local` - Loaded in all cases (local overrides, NOT checked in)
- `.env.production` - Loaded in production builds (checked in)
- `.env.production.local` - Loaded in production (local overrides, NOT checked in)
- `.env.staging` - Loaded for staging builds (checked in)
- `.env.staging.local` - Loaded for staging (local overrides, NOT checked in)
- `.env.https` - Special file for HTTPS development mode (checked in)
- `.env.example` - Template showing all available options (checked in)

**Note**: `.local` files should be added to `.gitignore` and never checked in.

## Configuration Variables

### VITE_API_URL (Required)
**Purpose**: The API endpoint URL that the frontend will use to communicate with the backend.

**Format**: Full URL including protocol and path
- HTTP example: `http://localhost:8000/api`
- HTTPS example: `https://api.example.com/api`
- Relative example: `/api` (uses same origin)

**Default**: `http://localhost:8000/api`

**Used in**: `frontend/src/services/api.ts`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
```

### VITE_USE_HTTPS (Optional)
**Purpose**: Enable HTTPS for local development with self-signed certificates.

**Valid values**: `true` or `false`

**Default**: `false`

**Used in**: `frontend/vite.config.ts` - Enables HTTPS server and loads SSL certificates

**Note**: Only affects local development (npm run dev). Production builds always use the protocol specified in VITE_API_URL.

### VITE_API_TARGET (Optional)
**Purpose**: Backend server URL for the Vite dev proxy. Enables development without CORS issues.

**Format**: Full URL including protocol (HTTP or HTTPS)

**Default**: `http://localhost:8000`

**Used in**: `frontend/vite.config.ts` - Proxy target for `/api` requests

**How it works**:
```
Browser Request:     GET https://localhost:3000/api/auth/login
         ↓
Vite Proxy:          GET http://localhost:8000/api/auth/login
         ↓
Backend Response:    {...}
```

### VITE_APP_NAME (Optional)
**Purpose**: Application name for branding and display purposes.

**Default**: `PQC-Secure`

**Usage**: Can be used in component headers, titles, and documentation

### VITE_API_TIMEOUT (Optional)
**Purpose**: Request timeout duration in milliseconds for API calls.

**Format**: Integer (milliseconds)

**Default**: `30000` (30 seconds)

**Usage**: Can be consumed in API client interceptors for timeout handling

### VITE_DEBUG (Optional)
**Purpose**: Enable debug mode for verbose logging and development tools.

**Valid values**: `true` or `false`

**Default**: `false`

**Usage**: Can be used to enable console logging and dev tools

## Deployment Scenarios

### Local Development (HTTP)

**.env** (or create `.env.local` for local overrides):
```
VITE_API_URL=http://localhost:8000/api
VITE_USE_HTTPS=false
VITE_API_TARGET=http://localhost:8000
VITE_DEBUG=true
```

**Start**:
```bash
npm run dev
# Opens on http://localhost:3000
```

### Local Development (HTTPS)

**.env.https** (included):
```
VITE_API_URL=https://localhost:3000/api
VITE_USE_HTTPS=true
VITE_API_TARGET=http://localhost:8000
```

**Start**:
```bash
npm run dev:https
# Opens on https://localhost:3000
# Self-signed certificates auto-generated
```

### Production Deployment

**Build for production**:
```bash
npm run build
# Reads .env.production
```

**.env.production** (adjust with your actual URLs):
```
VITE_API_URL=https://api.example.com/api
VITE_USE_HTTPS=false
VITE_APP_NAME=PQC-Secure
VITE_DEBUG=false
```

**Deployment**:
- Static frontend served by web server (nginx, Apache, S3, etc.)
- All API requests go to `https://api.example.com/api`
- Backend handles CORS for `https://example.com` origin

### Staging Deployment

**Build for staging**:
```bash
npm run build -- --mode staging
# Reads .env.staging
```

**.env.staging**:
```
VITE_API_URL=https://staging-api.example.com/api
VITE_DEBUG=true
```

### Docker Deployment

Dockerfile snippet for production:
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY frontend ./
RUN npm install
RUN npm run build -- --mode production

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Pass environment to build:
```bash
docker build \
  --build-arg VITE_API_URL=https://api.example.com/api \
  -t pqc-secure-frontend:latest .
```

## Using Environment Variables in Code

### In Components/Services

```typescript
// Get environment variable
const apiUrl = import.meta.env.VITE_API_URL

// With fallback
const appName = import.meta.env.VITE_APP_NAME || 'PQC-Secure'

// Check if in development
if (import.meta.env.DEV) {
  console.log('Development mode')
}

// Check if in production
if (import.meta.env.PROD) {
  console.log('Production mode')
}

// Get custom mode
if (import.meta.env.MODE === 'staging') {
  console.log('Staging mode')
}
```

### Type Safety (TypeScript)

Create `frontend/src/env.d.ts`:
```typescript
interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_USE_HTTPS: string
  readonly VITE_API_TARGET: string
  readonly VITE_APP_NAME: string
  readonly VITE_API_TIMEOUT: string
  readonly VITE_DEBUG: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

This is already configured in the project.

## Development Workflow

### Setting Up Local Development

1. **First time setup**:
   ```bash
   cd frontend
   npm install
   ```

2. **Create local overrides** (optional):
   ```bash
   cp .env .env.local
   # Edit .env.local with your settings
   ```

3. **Start development**:
   ```bash
   npm run dev
   # Uses .env + .env.local (if exists)
   ```

### Using Different Backends

**Default (localhost)**:
```bash
npm run dev
# Uses http://localhost:8000/api
```

**Remote staging backend** (create .env.local):
```
VITE_API_URL=https://staging-api.example.com/api
VITE_API_TARGET=https://staging-api.example.com
```
```bash
npm run dev
```

**Specific port**:
```bash
VITE_API_TARGET=http://localhost:8001 npm run dev
```

### Building for Different Environments

```bash
# Production build
npm run build
# Reads .env.production

# Staging build
npm run build -- --mode staging
# Reads .env.staging

# Production build with custom API
VITE_API_URL=https://custom-api.example.com/api npm run build
```

## Troubleshooting

### "API requests return 404"
- Check `VITE_API_URL` matches your backend address
- Verify backend is running on the specified host/port
- Check CORS configuration on backend

### "Mixed content warning in browser"
- Frontend is HTTPS but API is HTTP (insecure)
- Use HTTPS for both or HTTP for both
- In production, always use HTTPS for both

### "API calls to wrong host"
- Verify `VITE_API_URL` is set correctly
- Check browser DevTools → Network tab → Request URL
- Clear browser cache or use incognito mode

### "Environment variable not loaded"
- Variable must start with `VITE_` prefix
- File must be in project root (`frontend/.env`, not in `src/`)
- Dev server must be restarted after changing `.env` file
- Build must be run after changing for production

### "Local .env changes not reflected"
- Stop dev server (Ctrl+C)
- Restart dev server: `npm run dev`
- Environment variables are read at startup

## Security Considerations

### Do NOT Check In These Files
- `.env.local` - Contains local overrides and secrets
- `.env.*.local` - Environment-specific local overrides
- Any files with real credentials or tokens

### Best Practices
1. **Use `.env.example`** to document all available variables
2. **Use `.local` files** for machine-specific configuration
3. **Use CI/CD secrets** for production API URLs and tokens
4. **Never log** API URLs containing credentials
5. **Use HTTPS** in production for all communication
6. **Rotate credentials** if accidentally committed

### Production Security
- Store API URLs in CI/CD pipeline secrets
- Use environment-specific build processes
- Never embed user tokens or API keys in code
- Always use HTTPS for API communication
- Implement request timeouts (VITE_API_TIMEOUT)

## References

- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [Vite Server Configuration](https://vitejs.dev/config/server-options.html)
- [HTTPS Local Development](./HTTPS_SETUP.md)
- [Build Tooling](./BUILD_TOOLING.md)

## Environment Variable Reference

| Variable | Type | Default | Scope | Description |
|----------|------|---------|-------|-------------|
| `VITE_API_URL` | URL | `http://localhost:8000/api` | Client | Backend API endpoint |
| `VITE_USE_HTTPS` | Boolean | `false` | Dev Only | Enable HTTPS in dev |
| `VITE_API_TARGET` | URL | `http://localhost:8000` | Dev Only | Proxy target |
| `VITE_APP_NAME` | String | `PQC-Secure` | Client | Application name |
| `VITE_API_TIMEOUT` | Integer | `30000` | Client | Request timeout (ms) |
| `VITE_DEBUG` | Boolean | `false` | Client | Debug mode |

## FAQ

**Q: Which .env file should I edit?**
A: For local development, create/edit `.env.local`. For CI/CD, use pipeline secrets. For version control, edit `.env` or environment-specific files (`.env.production`, `.env.staging`).

**Q: How do I use different APIs for different team members?**
A: Each developer creates their own `.env.local` with their configuration. This file is in `.gitignore` and not checked in.

**Q: Can I change the API URL at runtime?**
A: No, environment variables are embedded at build time. To change them, rebuild the application with different environment variables.

**Q: Why is VITE_API_TARGET different from VITE_API_URL?**
A: `VITE_API_TARGET` is only used by the dev server proxy. `VITE_API_URL` is what the browser uses. This allows the proxy to reach a backend on a different network while the browser sees `/api`.

**Q: How do I deploy to multiple environments?**
A: Build once with `npm run build -- --mode production`, configure different `.env.production` files per environment, or pass build-time environment variables to the build process.

**Q: What if my backend is on a different domain?**
A: Set `VITE_API_URL` to the backend's full URL (e.g., `https://api.example.com/api`) and ensure CORS is configured on the backend to accept requests from your frontend origin.
