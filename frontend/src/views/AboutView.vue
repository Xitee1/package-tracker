<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('about.title') }}</h1>

    <!-- App Info Card -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <div class="flex items-center gap-3 mb-4">
        <div
          class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0"
        >
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ $t('app.title') }}
          </h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            {{ $t('about.appInfo') }}
          </p>
        </div>
      </div>

      <div class="space-y-3">
        <div class="flex items-center gap-2">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
            {{ $t('about.version') }}:
          </span>
          <span class="text-sm text-gray-900 dark:text-white font-mono">
            {{ version }}
          </span>
        </div>

        <div v-if="canCheckUpdates" class="flex items-center gap-3">
          <button
            @click="checkForUpdates"
            :disabled="updateStatus === 'checking'"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:not-disabled:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ updateStatus === 'checking' ? $t('about.checking') : $t('about.checkUpdates') }}
          </button>

          <span
            v-if="updateStatus === 'up-to-date'"
            class="inline-flex items-center gap-1.5 px-2.5 py-1 text-sm font-medium rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            {{ $t('about.upToDate') }}
          </span>

          <span
            v-if="updateStatus === 'update-available'"
            class="inline-flex items-center gap-1.5 px-2.5 py-1 text-sm font-medium rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
          >
            {{ $t('about.updateAvailable', { version: latestVersion }) }}
            <a
              :href="latestReleaseUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="underline hover:no-underline"
            >
              {{ $t('about.viewRelease') }}
            </a>
          </span>

          <span v-if="updateStatus === 'error'" class="text-sm text-red-600 dark:text-red-400">
            {{ $t('about.checkFailed') }}
          </span>
        </div>
      </div>
    </div>

    <!-- Links Card (hidden when no REPO_URL is configured) -->
    <div
      v-if="REPO_URL"
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {{ $t('about.links') }}
      </h2>

      <div class="flex flex-col items-start gap-3">
        <a
          v-for="link in links"
          :key="link.url"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          <span
            v-html="link.icon"
            class="w-5 h-5 flex-shrink-0 text-gray-400 dark:text-gray-500"
          ></span>
          {{ link.label }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'

const { t } = useI18n()

const version = ref(__APP_VERSION__)
const updateStatus = ref<'idle' | 'checking' | 'up-to-date' | 'update-available' | 'error'>('idle')
const latestVersion = ref('')
const latestReleaseUrl = ref('')

const REPO_URL = __REPO_URL__

/** Extract GitHub "owner/repo" from a GitHub URL, or null if not GitHub */
function getGitHubRepo(url: string): string | null {
  const match = url.match(/^https?:\/\/github\.com\/([^/]+\/[^/]+)\/?$/)
  return match ? match[1] : null
}

const githubRepo = REPO_URL ? getGitHubRepo(REPO_URL) : null
const canCheckUpdates = !!githubRepo

const links = computed(() => {
  const items: { label: string; url: string; icon: string }[] = []
  if (!REPO_URL) return items

  items.push(
    {
      label: t('about.sourceCode'),
      url: REPO_URL,
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>',
    },
    {
      label: t('about.issues'),
      url: `${REPO_URL}/issues`,
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
    },
    {
      label: t('about.releases'),
      url: `${REPO_URL}/releases`,
      icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" /></svg>',
    },
  )

  return items
})

function isValidVersion(v: string): boolean {
  const normalized = v.replace(/^v/, '')
  return /^\d+(\.\d+)*$/.test(normalized)
}

async function fetchVersion() {
  try {
    const { data } = await api.get('/version')
    version.value = data.version
  } catch {
    version.value = '?'
  }
}

function compareVersions(a: string, b: string): number {
  // Handle invalid versions (non-numeric like "?", "unknown", etc.)
  // Treat invalid versions as older than any valid version
  const aValid = isValidVersion(a)
  const bValid = isValidVersion(b)

  // If neither is valid, consider them equal
  if (!aValid && !bValid) return 0
  // If only a is invalid, it's older
  if (!aValid) return -1
  // If only b is invalid, a is newer
  if (!bValid) return 1

  // Both valid, compare numerically
  const pa = a.replace(/^v/, '').split('.').map(Number)
  const pb = b.replace(/^v/, '').split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] || 0
    const nb = pb[i] || 0
    if (na > nb) return 1
    if (na < nb) return -1
  }
  return 0
}

async function checkForUpdates() {
  if (!githubRepo) return

  updateStatus.value = 'checking'
  try {
    if (!isValidVersion(version.value)) {
      throw new Error('Cannot check for updates: current version is unknown')
    }

    const resp = await fetch(`https://api.github.com/repos/${githubRepo}/releases/latest`)
    if (!resp.ok) throw new Error('GitHub API error')
    const data = await resp.json()

    if (!data || typeof data !== 'object') {
      throw new Error('Invalid GitHub API response')
    }

    const latest = (data as any).tag_name
    const latestUrl = (data as any).html_url

    if (typeof latest !== 'string' || typeof latestUrl !== 'string') {
      throw new Error('Missing required fields in GitHub API response')
    }

    latestVersion.value = latest
    latestReleaseUrl.value = latestUrl

    if (compareVersions(version.value, latest) >= 0) {
      updateStatus.value = 'up-to-date'
    } else {
      updateStatus.value = 'update-available'
    }
  } catch {
    updateStatus.value = 'error'
  }
}
</script>
