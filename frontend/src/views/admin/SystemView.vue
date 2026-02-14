<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Top Bar -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('system.title') }}</h1>
        <p v-if="lastRefreshedAt" class="text-xs text-gray-400 dark:text-gray-500 mt-1">
          {{ t('system.lastRefreshed', { seconds: secondsSinceRefresh }) }}
        </p>
      </div>
      <button
        @click="refresh"
        :disabled="loading"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50"
      >
        <svg
          class="w-4 h-4"
          :class="{ 'animate-spin': loading }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        {{ t('common.refresh') }}
      </button>
    </div>

    <!-- Error Banner -->
    <div
      v-if="error"
      class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-6"
    >
      {{ error }}
    </div>

    <!-- Loading State -->
    <div v-if="loading && !status" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ t('system.loadingStatus') }}
    </div>

    <template v-if="status">
      <!-- Global Summary Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <!-- Watched Folders -->
        <div
          class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
        >
          <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
            {{ t('system.watchedFolders') }}
          </p>
          <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {{
              t('system.watchedFoldersValue', {
                running: status.global.running,
                total: status.global.total_folders,
              })
            }}
          </p>
        </div>

        <!-- Processing -->
        <div
          class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
        >
          <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
            {{ t('system.processing') }}
          </p>
          <p
            class="text-2xl font-bold mt-1"
            :class="
              status.global.processing_folders > 0
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-gray-400 dark:text-gray-500'
            "
          >
            <template v-if="status.global.processing_folders > 0">
              {{
                t('system.processingValue', {
                  count: status.global.queue_total,
                  folders: status.global.processing_folders,
                })
              }}
            </template>
            <template v-else>
              {{ t('system.processingIdle') }}
            </template>
          </p>
        </div>

        <!-- Errors -->
        <div
          class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
        >
          <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
            {{ t('system.errors') }}
          </p>
          <p
            class="text-2xl font-bold mt-1"
            :class="
              status.global.errors > 0
                ? 'text-red-600 dark:text-red-400'
                : 'text-gray-400 dark:text-gray-500'
            "
          >
            {{ status.global.errors }}
          </p>
        </div>
      </div>

      <!-- Queue Stats Card -->
      <div
        v-if="queueStats"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ t('system.queueStats') }}
          </h2>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 p-5">
          <div class="text-center">
            <p class="text-2xl font-bold text-gray-500 dark:text-gray-400">
              {{ queueStats.queued }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusQueued') }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {{ queueStats.processing }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusProcessing') }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-green-600 dark:text-green-400">
              {{ queueStats.completed }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusCompleted') }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-red-600 dark:text-red-400">
              {{ queueStats.failed }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusFailed') }}
            </p>
          </div>
        </div>
      </div>

      <!-- Scheduled Jobs -->
      <div
        v-if="status.scheduled_jobs?.length"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ t('system.scheduledJobs') }}
          </h2>
        </div>
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <div
            v-for="job in status.scheduled_jobs"
            :key="job.id"
            class="px-5 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
          >
            <div>
              <p class="text-sm font-medium text-gray-900 dark:text-white">
                {{ job.description }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ t('system.jobInterval', { seconds: job.interval_seconds }) }}
              </p>
            </div>
            <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              <span v-if="job.last_status">
                {{ t('system.jobLastStatus') }}:
                <span
                  class="font-medium"
                  :class="
                    job.last_status === 'error'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-green-600 dark:text-green-400'
                  "
                >
                  {{ job.last_status }}
                </span>
              </span>
              <span>
                {{ t('system.jobLastRun') }}:
                {{ job.last_run_at ? formatTimeAgo(job.last_run_at) : t('system.jobNever') }}
              </span>
              <span>
                {{ t('system.jobNextRun') }}:
                {{ job.next_run_at ? formatTimeUntil(job.next_run_at) : t('system.jobNever') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- User-Grouped Folder List -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ t('system.watchedFolders') }}
          </h2>
        </div>

        <div
          v-if="status.users.length === 0 || allFoldersCount === 0"
          class="p-8 text-center text-gray-500 dark:text-gray-400 text-sm"
        >
          {{ t('system.noFolders') }}
        </div>

        <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
          <div v-for="user in status.users" :key="user.user_id">
            <!-- User Header -->
            <button
              @click="toggleUser(user.user_id)"
              class="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div class="flex items-center gap-3">
                <svg
                  class="w-4 h-4 text-gray-400 transition-transform duration-200"
                  :class="{ 'rotate-90': expandedUsers.has(user.user_id) }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 5l7 7-7 7"
                  />
                </svg>
                <span class="text-sm font-semibold text-gray-900 dark:text-white">
                  {{ user.username }}
                </span>
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {{ t('system.foldersCount', { count: userFolderCount(user) }) }}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <span
                  v-if="userQueueTotal(user) > 0"
                  class="text-xs text-amber-600 dark:text-amber-400"
                >
                  {{ t('system.emailsQueued', { count: userQueueTotal(user) }) }}
                </span>
              </div>
            </button>

            <!-- Expanded User Content -->
            <div v-if="expandedUsers.has(user.user_id)" class="pb-2">
              <div v-for="account in user.accounts" :key="account.account_id" class="px-5">
                <!-- Account Sub-header -->
                <div class="flex items-center gap-2 py-2 pl-7">
                  <svg
                    class="w-4 h-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                  <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {{ account.account_name }}
                  </span>
                  <span
                    v-if="!account.is_active"
                    class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                  >
                    {{ t('common.inactive') }}
                  </span>
                </div>

                <!-- Folder Cards -->
                <div class="space-y-2 pl-7 pb-3">
                  <div
                    v-for="folder in account.folders"
                    :key="folder.folder_id"
                    class="border border-gray-200 dark:border-gray-700 rounded-md p-3"
                  >
                    <!-- Folder Path + Mode Badge -->
                    <div class="flex items-center justify-between mb-2">
                      <span class="text-sm font-medium text-gray-900 dark:text-white">
                        {{ folder.folder_path }}
                      </span>
                      <span
                        class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                        :class="modeColor(folder.mode)"
                      >
                        <span
                          class="w-1.5 h-1.5 rounded-full"
                          :class="modeDotColor(folder.mode)"
                        ></span>
                        {{ modeLabel(folder.mode, folder) }}
                      </span>
                    </div>

                    <!-- Timing Line -->
                    <div
                      class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400"
                    >
                      <span v-if="folder.last_activity_at">
                        {{
                          t('system.lastActivity', { time: formatTimeAgo(folder.last_activity_at) })
                        }}
                      </span>
                      <span v-if="folder.last_scan_at">
                        {{ t('system.lastScan', { time: formatTimeAgo(folder.last_scan_at) }) }}
                      </span>
                      <span v-if="folder.mode === 'polling' && folder.next_scan_at">
                        {{ t('system.nextCheck', { time: formatTimeUntil(folder.next_scan_at) }) }}
                      </span>
                    </div>

                    <!-- Queue Line -->
                    <div class="mt-1.5 text-xs">
                      <template v-if="folder.queue_total > 0 && folder.mode === 'processing'">
                        <span class="text-amber-600 dark:text-amber-400 font-medium">
                          {{
                            t('system.queueProcessing', {
                              position: folder.queue_position,
                              total: folder.queue_total,
                            })
                          }}
                        </span>
                        <div
                          v-if="folder.current_email_subject"
                          class="text-gray-500 dark:text-gray-400 mt-0.5 truncate"
                        >
                          {{ folder.current_email_subject }}
                          <span v-if="folder.current_email_sender" class="ml-1">
                            &mdash; {{ folder.current_email_sender }}
                          </span>
                        </div>
                      </template>
                      <template v-else>
                        <span class="text-gray-400 dark:text-gray-500">
                          {{ t('system.queueIdle') }}
                        </span>
                      </template>
                    </div>

                    <!-- Error Section -->
                    <div
                      v-if="folder.error"
                      class="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded px-2 py-1.5"
                    >
                      {{ folder.error }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { useQueueStore, type QueueStats } from '@/stores/queue'

const { t } = useI18n()
const queueStore = useQueueStore()

// --- Type Definitions ---

interface FolderStatus {
  folder_id: number
  folder_path: string
  running: boolean
  mode: string
  last_scan_at: string | null
  next_scan_at: string | null
  last_activity_at: string | null
  queue_total: number
  queue_position: number
  current_email_subject: string | null
  current_email_sender: string | null
  error: string | null
}

interface AccountStatus {
  account_id: number
  account_name: string
  is_active: boolean
  folders: FolderStatus[]
}

interface UserStatus {
  user_id: number
  username: string
  accounts: AccountStatus[]
}

interface GlobalSummary {
  total_folders: number
  running: number
  errors: number
  queue_total: number
  processing_folders: number
}

interface ScheduledJob {
  id: string
  description: string
  interval_seconds: number
  last_run_at: string | null
  next_run_at: string | null
  last_status: string | null
}

interface SystemStatus {
  global: GlobalSummary
  users: UserStatus[]
  scheduled_jobs?: ScheduledJob[]
}

// --- State ---

const status = ref<SystemStatus | null>(null)
const queueStats = ref<QueueStats | null>(null)
const loading = ref(false)
const error = ref('')
const lastRefreshedAt = ref<Date | null>(null)
const secondsSinceRefresh = ref(0)
const expandedUsers = ref<Set<number>>(new Set())

let pollInterval: ReturnType<typeof setInterval> | null = null
let tickInterval: ReturnType<typeof setInterval> | null = null

// --- Computed ---

const allFoldersCount = computed(() => {
  if (!status.value) return 0
  return status.value.users.reduce(
    (sum, user) => sum + user.accounts.reduce((aSum, account) => aSum + account.folders.length, 0),
    0,
  )
})

// --- Helper Functions ---

function formatTimeAgo(isoString: string | null): string {
  if (!isoString) return '-'
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  if (diffMs < 0) return 'just now'

  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'

  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`

  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}h ago`

  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay}d ago`
}

function formatTimeUntil(isoString: string | null): string {
  if (!isoString) return '-'
  const now = Date.now()
  const target = new Date(isoString).getTime()
  const diffMs = target - now
  if (diffMs <= 0) return 'now'

  const diffSec = Math.floor(diffMs / 1000)
  const minutes = Math.floor(diffSec / 60)
  const seconds = diffSec % 60

  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

function modeLabel(mode: string, folder?: FolderStatus): string {
  const labels: Record<string, string> = {
    idle: t('system.modeIdle'),
    polling: t('system.modePolling'),
    processing: t('system.modeProcessing'),
    connecting: t('system.modeConnecting'),
    stopped: t('system.modeStopped'),
    unknown: t('system.modeUnknown'),
  }

  if (mode === 'error_backoff') {
    const seconds = folder?.next_scan_at
      ? Math.max(0, Math.floor((new Date(folder.next_scan_at).getTime() - Date.now()) / 1000))
      : 0
    return t('system.modeErrorBackoff', { seconds })
  }

  return labels[mode] || t('system.modeUnknown')
}

function modeColor(mode: string): string {
  const colors: Record<string, string> = {
    idle: 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400',
    polling: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-400',
    processing: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-400',
    connecting: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    error_backoff: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-400',
    stopped: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  }
  return colors[mode] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
}

function modeDotColor(mode: string): string {
  const colors: Record<string, string> = {
    idle: 'bg-green-500',
    polling: 'bg-blue-500',
    processing: 'bg-amber-500',
    connecting: 'bg-gray-400',
    error_backoff: 'bg-red-500',
    stopped: 'bg-gray-400',
  }
  return colors[mode] || 'bg-gray-400'
}

function userFolderCount(user: UserStatus): number {
  return user.accounts.reduce((sum, account) => sum + account.folders.length, 0)
}

function userQueueTotal(user: UserStatus): number {
  return user.accounts.reduce(
    (sum, account) => sum + account.folders.reduce((fSum, folder) => fSum + folder.queue_total, 0),
    0,
  )
}

function toggleUser(userId: number) {
  if (expandedUsers.value.has(userId)) {
    expandedUsers.value.delete(userId)
  } else {
    expandedUsers.value.add(userId)
  }
}

// --- Data Fetching ---

async function fetchStatus() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<SystemStatus>('/system/status')
    status.value = res.data

    lastRefreshedAt.value = new Date()
    secondsSinceRefresh.value = 0
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('system.loadFailed')
  } finally {
    loading.value = false
  }
}

async function fetchQueueStats() {
  try {
    queueStats.value = await queueStore.fetchStats()
  } catch {
    // Queue stats are non-critical; silently ignore
    queueStats.value = null
  }
}

async function refresh() {
  await Promise.all([fetchStatus(), fetchQueueStats()])
}

// --- Lifecycle ---

onMounted(() => {
  refresh()

  // Auto-poll every 30 seconds
  pollInterval = setInterval(() => {
    refresh()
  }, 30000)

  // Tick the "last refreshed" counter every second
  tickInterval = setInterval(() => {
    if (lastRefreshedAt.value) {
      secondsSinceRefresh.value = Math.floor((Date.now() - lastRefreshedAt.value.getTime()) / 1000)
    }
  }, 1000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  if (tickInterval) clearInterval(tickInterval)
})
</script>
