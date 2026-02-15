<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('about.title') }}</h1>

    <!-- App Info Card -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <div class="flex items-center gap-3 mb-4">
        <div class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
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
          <span v-if="version" class="text-sm text-gray-900 dark:text-white font-mono">
            {{ version }}
          </span>
          <span v-else class="text-sm text-gray-400 dark:text-gray-500">
            {{ $t('common.loading') }}
          </span>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="checkForUpdates"
            :disabled="updateStatus === 'checking'"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
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

    <!-- Links Card -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {{ $t('about.links') }}
      </h2>

      <div class="space-y-3">
        <a
          v-for="link in links"
          :key="link.url"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-3 text-sm text-blue-600 dark:text-blue-400 hover:underline"
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
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'

const { t } = useI18n()

const version = ref('')
const updateStatus = ref<'idle' | 'checking' | 'up-to-date' | 'update-available' | 'error'>('idle')
const latestVersion = ref('')
const latestReleaseUrl = ref('')

const GITHUB_REPO = 'Xitee1/package-tracker'

const links = computed(() => [
  {
    label: t('about.githubRepo'),
    url: `https://github.com/${GITHUB_REPO}`,
    icon: '<svg fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>',
  },
  {
    label: t('about.issues'),
    url: `https://github.com/${GITHUB_REPO}/issues`,
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>',
  },
  {
    label: t('about.releases'),
    url: `https://github.com/${GITHUB_REPO}/releases`,
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" /></svg>',
  },
  {
    label: t('about.license'),
    url: `https://github.com/${GITHUB_REPO}/blob/main/LICENSE`,
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>',
  },
])

async function fetchVersion() {
  try {
    const { data } = await api.get('/version')
    version.value = data.version
  } catch {
    version.value = '?'
  }
}

function compareVersions(a: string, b: string): number {
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
  updateStatus.value = 'checking'
  try {
    const resp = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`)
    if (!resp.ok) throw new Error('GitHub API error')
    const data = await resp.json()
    const latest = data.tag_name as string
    latestVersion.value = latest
    latestReleaseUrl.value = data.html_url as string

    if (compareVersions(version.value, latest) >= 0) {
      updateStatus.value = 'up-to-date'
    } else {
      updateStatus.value = 'update-available'
    }
  } catch {
    updateStatus.value = 'error'
  }
}

onMounted(fetchVersion)
</script>
