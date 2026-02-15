# hatch-vcs Versioning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded version strings with git-tag-derived versions using hatch-vcs (backend) and git describe via Vite config (frontend).

**Architecture:** Backend switches from setuptools to hatchling + hatch-vcs, which derives the version from git tags at build/install time. Frontend injects a compile-time `__APP_VERSION__` constant via Vite's `define` option using `child_process.execSync('git describe')`. Docker builds receive the version via `--build-arg` since they lack git history.

**Tech Stack:** hatchling, hatch-vcs, Vite define, child_process, Docker build args

---

### Task 1: Switch backend build system to hatchling + hatch-vcs

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: Update pyproject.toml**

Replace the `[build-system]` section and update `[project]` to use dynamic versioning:

```toml
[project]
name = "package-tracker"
dynamic = ["version"]
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "bcrypt>=4.0.0,<5.0.0",
    "cryptography>=44.0.0",
    "litellm>=1.55.0",
    "aioimaplib>=2.0.0",
    "html2text>=2024.0.0",
    "python-multipart>=0.0.18",
    "python-dotenv>=1.0.0",
    "apscheduler>=4.0.0a1",
    "email-validator>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
    "aiosqlite>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"
raw-options = { root = ".." }

[tool.hatch.build.hooks.vcs]
version-file = "app/_version.py"
```

Changes from original:
- Remove `version = "0.1.0"`, add `dynamic = ["version"]`
- Replace `[build-system]` from setuptools to hatchling + hatch-vcs
- Add `[tool.hatch.version]` with `source = "vcs"` and `root = ".."`
- Add `[tool.hatch.build.hooks.vcs]` with `version-file = "app/_version.py"`

**Step 2: Add `_version.py` to .gitignore**

Create `backend/.gitignore` (does not exist yet):

```
app/_version.py
```

**Step 3: Reinstall backend in dev mode and verify**

Run from `backend/`:
```bash
pip install -e ".[dev]"
```

Then verify the version is derived from git:
```bash
python -c "from importlib.metadata import version; print(version('package-tracker'))"
```

Expected: a version string like `0.1.dev231+g2106eb9` (since there's no `v*` tag yet, hatch-vcs uses fallback versioning).

**Step 4: Verify `app/_version.py` was generated**

```bash
cat app/_version.py
```

Expected: file exists with `__version__` and `__version_tuple__` variables.

**Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.gitignore
git commit -m "build: switch backend to hatchling + hatch-vcs for automatic versioning"
```

---

### Task 2: Add `__APP_VERSION__` to frontend via Vite config

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/env.d.ts`

**Step 1: Update vite.config.ts**

Add `execSync` import and `getGitVersion()` helper, then add `define` to the config:

```ts
import { execSync } from 'node:child_process'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

function getGitVersion(): string {
  if (process.env.APP_VERSION) return process.env.APP_VERSION
  try {
    return execSync('git describe --tags --always --dirty').toString().trim().replace(/^v/, '')
  } catch {
    return '0.0.0-unknown'
  }
}

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  define: {
    __APP_VERSION__: JSON.stringify(getGitVersion()),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://backend:8000',
    },
  },
})
```

**Step 2: Declare the global type in `env.d.ts`**

Update `frontend/env.d.ts`:

```ts
/// <reference types="vite/client" />

declare const __APP_VERSION__: string
```

**Step 3: Verify the frontend builds**

Run from `frontend/`:
```bash
npm run build
```

Expected: build succeeds without errors.

**Step 4: Commit**

```bash
git add frontend/vite.config.ts frontend/env.d.ts
git commit -m "build: inject git-derived __APP_VERSION__ at frontend build time"
```

---

### Task 3: Update AboutView.vue to use compile-time version

**Files:**
- Modify: `frontend/src/views/AboutView.vue`

**Step 1: Replace the API-fetched version with `__APP_VERSION__`**

In the `<script setup>` section, make these changes:

1. Remove the `api` import (line 120: `import api from '@/api/client'`)
2. Change `const version = ref('')` to `const version = __APP_VERSION__`
3. Remove the `fetchVersion()` function (lines 154-161)
4. Remove the `onMounted(fetchVersion)` call (line 195)
5. Remove `onMounted` from the vue import since it's no longer needed (but check if other code uses it — `checkForUpdates` does NOT use onMounted, it was only used for fetchVersion)

In the `<template>` section:
1. The version display currently uses `v-if="version"` / `v-else` for loading state. Since `version` is now a constant string (always truthy), remove the `v-else` loading span and simplify:
   - Remove the `v-if="version"` directive from the version display span (it's always present now)
   - Remove the `v-else` loading span entirely

Updated `<script setup>`:
```ts
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const version = __APP_VERSION__
const updateStatus = ref<'idle' | 'checking' | 'up-to-date' | 'update-available' | 'error'>('idle')
const latestVersion = ref('')
const latestReleaseUrl = ref('')

const GITHUB_REPO = 'Xitee1/package-tracker'

const links = computed(() => [
  // ... unchanged
])

function compareVersions(a: string, b: string): number {
  // ... unchanged
}

async function checkForUpdates() {
  // ... unchanged
}
```

Updated template version display (replace lines 31-41):
```html
<div class="flex items-center gap-2">
  <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
    {{ $t('about.version') }}:
  </span>
  <span class="text-sm text-gray-900 dark:text-white font-mono">
    {{ version }}
  </span>
</div>
```

**Step 2: Verify type-check passes**

```bash
npm run type-check
```

Expected: no errors.

**Step 3: Verify build succeeds**

```bash
npm run build
```

Expected: build succeeds.

**Step 4: Commit**

```bash
git add frontend/src/views/AboutView.vue
git commit -m "feat: use compile-time version in About page instead of API call"
```

---

### Task 4: Update Docker builds to pass version via build arg

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `frontend/Dockerfile`
- Modify: `frontend/Dockerfile.prod`
- Modify: `Dockerfile.prod`

**Step 1: Update `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ARG APP_VERSION=0.0.0-dev

COPY pyproject.toml .
RUN SETUPTOOLS_SCM_PRETEND_VERSION=${APP_VERSION} pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: Update `frontend/Dockerfile`**

The dev Dockerfile runs `npm run dev` which rebuilds on the fly. Since the dev container has the full source mounted, and `git describe` should work if `.git` is accessible, we only need a fallback. Add `APP_VERSION` arg:

```dockerfile
FROM node:20-alpine

WORKDIR /app

ARG APP_VERSION=0.0.0-dev
ENV APP_VERSION=${APP_VERSION}

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

**Step 3: Update `frontend/Dockerfile.prod`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app

ARG APP_VERSION=0.0.0-dev
ENV APP_VERSION=${APP_VERSION}

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Step 4: Update root `Dockerfile.prod`**

```dockerfile
# Stage 1: Build Vue frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app

ARG APP_VERSION=0.0.0-dev
ENV APP_VERSION=${APP_VERSION}

COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS backend-build
WORKDIR /app

ARG APP_VERSION=0.0.0-dev

COPY backend/pyproject.toml .
RUN SETUPTOOLS_SCM_PRETEND_VERSION=${APP_VERSION} pip install --no-cache-dir .

# Stage 3: Runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from build stage
COPY --from=backend-build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin

# Copy backend code
WORKDIR /app
COPY backend/ .

# Copy built frontend
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Copy configs
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Remove default nginx site
RUN rm -f /etc/nginx/sites-enabled/default

EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

**Step 5: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile frontend/Dockerfile.prod Dockerfile.prod
git commit -m "build: add APP_VERSION build arg to all Dockerfiles"
```

---

### Task 5: Update CI workflow to pass version build arg

**Files:**
- Modify: `.github/workflows/docker-publish.yml`

**Step 1: Update the workflow**

Add a step to extract the version from the git tag, and pass it as a build arg. The `docker/metadata-action` already extracts the version — we can derive it from the git ref:

```yaml
name: Build and push Docker image

on:
  push:
    tags:
      - 'v*'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Extract version from tag
        id: version
        run: echo "version=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: Dockerfile.prod
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          build-args: |
            APP_VERSION=${{ steps.version.outputs.version }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Changes:
- Added "Extract version from tag" step that strips the `v` prefix from the tag name
- Added `build-args` to the `docker/build-push-action` step

**Step 2: Commit**

```bash
git add .github/workflows/docker-publish.yml
git commit -m "ci: pass APP_VERSION build arg to Docker build"
```

---

### Task 6: Verify everything works end-to-end

**Step 1: Verify backend version locally**

From `backend/`:
```bash
pip install -e ".[dev]"
python -c "from importlib.metadata import version; print(version('package-tracker'))"
```

Expected: version string derived from git (e.g., `0.1.dev231+g2106eb9`).

**Step 2: Verify frontend build**

From `frontend/`:
```bash
npm run build
```

Expected: build succeeds. Check that `__APP_VERSION__` is injected by searching the build output:
```bash
grep -r "0.1.dev\|alpha-0.0.1\|unknown" dist/assets/ || echo "Version string embedded (check manually)"
```

**Step 3: Verify Docker dev build**

From project root:
```bash
docker compose build
```

Expected: both backend and frontend services build successfully.

**Step 4: Verify type-check and lint**

From `frontend/`:
```bash
npm run type-check
npm run lint
```

Expected: no errors.
