# Automatic Versioning with hatch-vcs

## Summary

Replace hardcoded version strings with git-tag-derived versions using hatch-vcs (backend) and git describe via Vite config (frontend). Both backend and frontend versions are derived from the same git tags (`v*` format).

## Backend: hatchling + hatch-vcs

Switch the build system from setuptools to hatchling with hatch-vcs.

**pyproject.toml changes:**
- Build system: `hatchling` + `hatch-vcs`
- Version field: `dynamic = ["version"]` (remove static `version = "0.1.0"`)
- VCS config: `source = "vcs"`, `root = ".."` (git root is parent of backend/)
- Version file: `app/_version.py` (auto-generated, gitignored)

**Version format:**
- Tagged commit: `0.2.0`
- Dev build (5 commits after v0.2.0): `0.2.1.dev5+g1234abc`

**Runtime:** `importlib.metadata.version("package-tracker")` in `version.py` continues to work unchanged.

## Frontend: Git describe in Vite config

Inject a compile-time constant via `vite.config.ts` using `child_process.execSync('git describe')`.

**Implementation:**
- `getGitVersion()` function in vite.config.ts tries `process.env.APP_VERSION` first, then `git describe --tags --always --dirty`, falls back to `0.0.0-unknown`
- Exposed as `__APP_VERSION__` via Vite `define`
- `AboutView.vue` uses `__APP_VERSION__` directly instead of fetching from backend API
- No extra npm dependencies needed

## Docker Builds

Docker containers lack git history, so version is passed via build args.

**Backend:** `SETUPTOOLS_SCM_PRETEND_VERSION` env var during `pip install`
**Frontend:** `APP_VERSION` env var read by `getGitVersion()` fallback
**Both:** `ARG APP_VERSION=0.0.0-dev` in Dockerfiles

CI workflow already extracts version from git tags; it passes `--build-arg APP_VERSION=...`.

## Files Changed

- `backend/pyproject.toml` — switch build system, dynamic version
- `backend/app/_version.py` — auto-generated (add to .gitignore)
- `backend/.gitignore` — add `app/_version.py`
- `frontend/vite.config.ts` — add `getGitVersion()` + `define`
- `frontend/src/vite-env.d.ts` — declare `__APP_VERSION__` global
- `frontend/src/views/AboutView.vue` — use `__APP_VERSION__` instead of API call
- `backend/Dockerfile` — add `ARG APP_VERSION`, set `SETUPTOOLS_SCM_PRETEND_VERSION`
- `frontend/Dockerfile` — add `ARG APP_VERSION`, set as env
- `frontend/Dockerfile.prod` — add `ARG APP_VERSION`, set as env
- `Dockerfile.prod` — add `ARG APP_VERSION`, propagate to both build stages
- `.github/workflows/docker-publish.yml` — pass `--build-arg APP_VERSION`

## Git Tags

- New tag format: `v{major}.{minor}.{patch}` (matches existing CI trigger `v*`)
- Old `alpha-0.0.1` tag is ignored by hatch-vcs (doesn't match `v*` pattern)
- First `v*` tag deferred to a later time
