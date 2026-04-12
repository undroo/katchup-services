/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BADMINTON_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
