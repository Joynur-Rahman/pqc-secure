# Frontend Build Tooling Guide

This document describes the build tooling, linting, and testing configuration for the PQC-Secure frontend.

## Build Tools

### Vite
- **Purpose**: Fast development server and production build tool
- **Config**: `vite.config.ts`
- **Features**:
  - Hot Module Replacement (HMR) for rapid development
  - Optimized production builds with tree-shaking
  - API proxy to backend (configured to `http://localhost:8000`)

### TypeScript
- **Version**: 5.7.2
- **Config**: `tsconfig.json` (references `tsconfig.app.json` and `tsconfig.node.json`)
- **Features**:
  - Strict mode enabled
  - JSX support with React 19
  - No unused variables or parameters allowed
  - Isolated modules for better compilation

## Linting

### ESLint
- **Version**: 9.19.0
- **Config**: `eslint.config.js` (new flat config format)
- **Plugins**:
  - `@eslint/js`: Core rules
  - `typescript-eslint`: TypeScript-specific rules
  - `eslint-plugin-react`: React-specific rules
  - `eslint-plugin-react-hooks`: React Hooks rules
  - `eslint-plugin-react-refresh`: React Fast Refresh compatibility

### Scripts
```bash
npm run lint           # Check for linting errors
npm run lint:fix      # Automatically fix linting errors
```

### Rules
- React doesn't need to be in scope (React 17+ JSX transform)
- React Fast Refresh components must be exported
- All React Hooks rules enforced
- No unused variables or parameters
- TypeScript strict mode compliance

## Testing

### Vitest
- **Version**: 2.1.8
- **Config**: `vitest.config.ts`
- **Environment**: jsdom (for DOM testing)
- **Features**:
  - Fast test execution
  - TypeScript support out of the box
  - ES modules compatible
  - Compatible with Jest syntax

### Testing Libraries
- `@testing-library/react`: React component testing utilities
- `@testing-library/vitest`: Vitest integration for Testing Library

### Scripts
```bash
npm run test          # Run tests once
npm run test:watch   # Run tests in watch mode
```

### Test Location
- Test files should be placed next to source files with `.test.ts` or `.test.tsx` suffix
- Example: `src/components/Button.tsx` → `src/components/Button.test.tsx`

### Writing Tests
```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MyComponent from './MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Expected Text')).toBeDefined()
  })
})
```

## Development Workflow

### Setup
```bash
cd frontend
npm install
```

### Development Server (HTTP)
```bash
npm run dev
```
- Starts on `http://localhost:3000`
- Auto-proxies `/api` requests to backend at `http://localhost:8000`

### Development Server (HTTPS)
```bash
npm run dev:https
```
- Starts on `https://localhost:3000`
- Auto-generates self-signed certificates if missing
- Auto-proxies `/api` requests to backend at `http://localhost:8000`
- See `HTTPS_SETUP.md` for detailed HTTPS configuration

### Build for Production
```bash
npm run build
```
- Type checks with TypeScript
- Bundles with Vite
- Output: `dist/` directory

### Code Quality Checks
```bash
npm run lint          # Check code style
npm run lint:fix     # Fix auto-fixable issues
npm run test         # Run all tests
npm run test:watch  # Run tests in watch mode
```

## Configuration Details

### ESLint Configuration
- Located in: `eslint.config.js`
- Format: ESLint flat config (new format)
- Ignores: `dist`, `node_modules`, `build`

### Vitest Configuration
- Located in: `vitest.config.ts`
- Coverage provider: v8
- Global test utilities available (no import needed for `describe`, `it`, `expect`)

### TypeScript Configuration
- Strict type checking enabled
- No implicit any
- No unused locals or parameters
- All strict checks enabled for better type safety

## Common Commands

```bash
# Development
npm run dev              # Start dev server (HTTP on port 3000)
npm run dev:https        # Start dev server (HTTPS on port 3000)

# Building
npm run build            # Production build
npm run preview          # Preview production build locally

# Code Quality
npm run lint             # Lint check
npm run lint:fix        # Fix linting issues
npm run test            # Run tests once
npm run test:watch     # Run tests in watch mode

# Cleanup
npm run clean            # Remove build artifacts (if configured)
```

## Troubleshooting

### ESLint Issues
- If ESLint config doesn't load: Delete `node_modules` and `npm install`
- If TypeScript files not linting: Ensure `.tsx` files are processed correctly

### Test Issues
- If tests won't run: Ensure `jsdom` environment is available
- If imports fail: Check that test files use `.test.ts` or `.test.tsx` suffix

### Build Issues
- If build fails: Run `npm run lint` to check for type errors
- If TypeScript complains: Check `tsconfig.app.json` for correct compiler options

### HTTPS Issues
- See `HTTPS_SETUP.md` for HTTPS-specific troubleshooting
- To disable HTTPS: Use `npm run dev` instead of `npm run dev:https`
- To regenerate certificates: Delete `frontend/certs/` and run `npm run dev:https`
