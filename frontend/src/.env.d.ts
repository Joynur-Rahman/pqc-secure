/// <reference types="vite/client" />

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
