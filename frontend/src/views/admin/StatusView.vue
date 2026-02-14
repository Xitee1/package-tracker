<template>
  <div>
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
    <div v-if="loading && !statusData" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ t('system.loadingStatus') }}
    </div>

    <template v-if="statusData">
      <!-- ==================== SYSTEM SECTION ==================== -->

      <!-- Queue Stats Card -->
      <div
        v-if="statusData.system"
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
              {{ statusData.system.queue.queued }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusQueued') }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {{ statusData.system.queue.processing }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusProcessing') }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-green-600 dark:text-green-400">
              {{ statusData.system.queue.completed }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusCompleted') }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-2xl font-bold text-red-600 dark:text-red-400">
              {{ statusData.system.queue.failed }}
            </p>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">
              {{ t('queue.statusFailed') }}
            </p>
          </div>
        </div>
      </div>

      <!-- Analyser Warning Banner -->
      <div
        v-if="noAnalyserConfigured"
        class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-md px-4 py-3 mb-6"
      >
        <div class="flex items-start gap-3">
          <svg
            class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <div class="flex-1">
            <p class="text-sm text-amber-800 dark:text-amber-300">
              {{
                queuedCount > 0
                  ? t('system.noAnalyserWarningQueued', { count: queuedCount })
                  : t('system.noAnalyserWarning')
              }}
            </p>
            <router-link
              to="/admin/analysers"
              class="inline-flex items-center gap-1 mt-2 text-sm font-medium text-amber-700 dark:text-amber-400 hover:text-amber-900 dark:hover:text-amber-300"
            >
              {{ t('system.configureAnalysers') }}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </router-link>
          </div>
        </div>
      </div>

      <!-- Scheduled Jobs -->
      <div
        v-if="statusData.system.scheduled_jobs?.length"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ t('system.scheduledJobs') }}
          </h2>
        </div>
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <div
            v-for="job in statusData.system.scheduled_jobs"
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

      <!-- ==================== MODULES SECTION ==================== -->

      <div v-if="statusData.modules.length > 0">
        <div v-for="(group, groupIdx) in groupedModules" :key="group.type">
          <!-- Type Divider -->
          <div class="flex items-center gap-3" :class="groupIdx === 0 ? 'mb-4' : 'mt-8 mb-4'">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white whitespace-nowrap">
              {{ group.label }}
            </h2>
            <div class="flex-1 border-t border-gray-200 dark:border-gray-700"></div>
          </div>

          <div class="space-y-4">
            <div
              v-for="mod in group.modules"
              :key="mod.key"
              class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
              :class="{ 'opacity-50': !mod.enabled }"
            >
              <!-- Module Card Header -->
              <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between">
                  <h3 class="text-base font-semibold text-gray-900 dark:text-white">
                    {{ mod.name }}
                  </h3>
                  <div class="flex items-center gap-2">
                    <span
                      v-if="!mod.enabled"
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                    >
                      {{ t('system.moduleDisabled') }}
                    </span>
                    <span
                      v-else-if="!mod.configured"
                      class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400"
                    >
                      {{ t('system.moduleNotConfigured') }}
                    </span>
                    <span
                      v-else-if="
                        mod.status && typeof mod.status === 'object' && 'mode' in mod.status
                      "
                      class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium"
                      :class="moduleModeColor(mod.status.mode as string)"
                    >
                      <span
                        class="w-1.5 h-1.5 rounded-full"
                        :class="moduleModeDotColor(mod.status.mode as string)"
                      ></span>
                      {{ moduleModeLabel(mod.status.mode as string) }}
                    </span>
                    <span
                      v-else
                      class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400"
                    >
                      <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                      {{ t('common.active') }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Module Card Body -->
              <div class="px-5 py-4">
                <!-- Disabled module -->
                <template v-if="!mod.enabled">
                  <p class="text-sm text-gray-500 dark:text-gray-400">{{ mod.description }}</p>
                </template>

                <!-- Unconfigured module -->
                <template v-else-if="!mod.configured">
                  <p class="text-sm text-gray-500 dark:text-gray-400">{{ mod.description }}</p>
                </template>

                <!-- No status data -->
                <template v-else-if="!mod.status">
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    {{ t('system.moduleNoStatus') }}
                  </p>
                </template>

                <!-- ===== EMAIL-USER module ===== -->
                <template v-else-if="mod.key === 'email-user'">
                  <div class="space-y-3">
                    <!-- Summary line -->
                    <div
                      class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600 dark:text-gray-400"
                    >
                      <span>
                        {{
                          t('system.watchedFoldersValue', {
                            running: (mod.status as EmailUserStatus).running,
                            total: (mod.status as EmailUserStatus).total_folders,
                          })
                        }}
                      </span>
                      <span
                        v-if="(mod.status as EmailUserStatus).errors > 0"
                        class="text-red-600 dark:text-red-400"
                      >
                        {{ (mod.status as EmailUserStatus).errors }}
                        {{ t('system.errors').toLowerCase() }}
                      </span>
                    </div>

                    <!-- User/Account/Folder tree -->
                    <div
                      v-if="
                        (mod.status as EmailUserStatus).users.length === 0 ||
                        emailUserFolderCount(mod.status as EmailUserStatus) === 0
                      "
                      class="text-sm text-gray-500 dark:text-gray-400"
                    >
                      {{ t('system.noFolders') }}
                    </div>

                    <div v-else class="divide-y divide-gray-200 dark:divide-gray-700 -mx-5">
                      <div
                        v-for="user in (mod.status as EmailUserStatus).users"
                        :key="user.user_id"
                      >
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
                          <div
                            v-for="account in user.accounts"
                            :key="account.account_id"
                            class="px-5"
                          >
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
                                      t('system.lastActivity', {
                                        time: formatTimeAgo(folder.last_activity_at),
                                      })
                                    }}
                                  </span>
                                  <span v-if="folder.last_scan_at">
                                    {{
                                      t('system.lastScan', {
                                        time: formatTimeAgo(folder.last_scan_at),
                                      })
                                    }}
                                  </span>
                                  <span v-if="folder.mode === 'polling' && folder.next_scan_at">
                                    {{
                                      t('system.nextCheck', {
                                        time: formatTimeUntil(folder.next_scan_at),
                                      })
                                    }}
                                  </span>
                                </div>

                                <!-- Queue Line -->
                                <div class="mt-1.5 text-xs">
                                  <template
                                    v-if="folder.queue_total > 0 && folder.mode === 'processing'"
                                  >
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

                <!-- ===== EMAIL-GLOBAL module ===== -->
                <template v-else-if="mod.key === 'email-global'">
                  <div class="space-y-3">
                    <!-- Mode badge + watching folder -->
                    <div class="flex items-center gap-3">
                      <span
                        class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                        :class="
                          modeColor(
                            (mod.status as EmailGlobalStatus).running
                              ? (mod.status as EmailGlobalStatus).mode
                              : 'stopped',
                          )
                        "
                      >
                        <span
                          class="w-1.5 h-1.5 rounded-full"
                          :class="
                            modeDotColor(
                              (mod.status as EmailGlobalStatus).running
                                ? (mod.status as EmailGlobalStatus).mode
                                : 'stopped',
                            )
                          "
                        ></span>
                        {{
                          modeLabel(
                            (mod.status as EmailGlobalStatus).running
                              ? (mod.status as EmailGlobalStatus).mode
                              : 'stopped',
                          )
                        }}
                      </span>
                    </div>

                    <!-- Info lines -->
                    <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                      <p>
                        {{
                          t('system.globalMailWatching', {
                            folder: (mod.status as EmailGlobalStatus).watching,
                          })
                        }}
                      </p>
                      <p>
                        {{
                          t('system.globalMailSenders', {
                            count: (mod.status as EmailGlobalStatus).registered_senders,
                          })
                        }}
                      </p>
                    </div>

                    <!-- Timing Line -->
                    <div
                      class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400"
                    >
                      <span v-if="(mod.status as EmailGlobalStatus).last_activity_at">
                        {{
                          t('system.lastActivity', {
                            time: formatTimeAgo((mod.status as EmailGlobalStatus).last_activity_at),
                          })
                        }}
                      </span>
                      <span v-if="(mod.status as EmailGlobalStatus).last_scan_at">
                        {{
                          t('system.lastScan', {
                            time: formatTimeAgo((mod.status as EmailGlobalStatus).last_scan_at),
                          })
                        }}
                      </span>
                      <span
                        v-if="
                          (mod.status as EmailGlobalStatus).mode === 'polling' &&
                          (mod.status as EmailGlobalStatus).next_scan_at
                        "
                      >
                        {{
                          t('system.nextCheck', {
                            time: formatTimeUntil((mod.status as EmailGlobalStatus).next_scan_at),
                          })
                        }}
                      </span>
                    </div>

                    <!-- Error -->
                    <div
                      v-if="(mod.status as EmailGlobalStatus).error"
                      class="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded px-2 py-1.5"
                    >
                      {{ (mod.status as EmailGlobalStatus).error }}
                    </div>
                  </div>
                </template>

                <!-- ===== LLM module ===== -->
                <template v-else-if="mod.key === 'llm'">
                  <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    <p>
                      {{
                        t('system.llmProvider', {
                          provider: (mod.status as LLMStatus).provider,
                        })
                      }}
                    </p>
                    <p>
                      {{
                        t('system.llmModel', {
                          model: (mod.status as LLMStatus).model,
                        })
                      }}
                    </p>
                  </div>
                </template>

                <!-- ===== Unknown module fallback ===== -->
                <template v-else>
                  <p class="text-sm text-gray-500 dark:text-gray-400">{{ mod.description }}</p>
                </template>
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

const { t } = useI18n()

// --- Type Definitions ---

interface ScheduledJob {
  id: string
  description: string
  interval_seconds: number
  last_run_at: string | null
  next_run_at: string | null
  last_status: string | null
}

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

interface EmailUserStatus {
  total_folders: number
  running: number
  errors: number
  users: UserStatus[]
}

interface EmailGlobalStatus {
  watching: string
  running: boolean
  mode: string
  registered_senders: number
  last_scan_at: string | null
  next_scan_at: string | null
  last_activity_at: string | null
  error: string | null
}

interface LLMStatus {
  provider: string
  model: string
  mode: string
}

interface ModuleEntry {
  key: string
  name: string
  type: string
  version: string
  description: string
  enabled: boolean
  configured: boolean
  status: Record<string, unknown> | null
}

interface SystemInfo {
  queue: { queued: number; processing: number; completed: number; failed: number }
  scheduled_jobs: ScheduledJob[]
}

interface StatusResponse {
  system: SystemInfo
  modules: ModuleEntry[]
}

// --- State ---

const statusData = ref<StatusResponse | null>(null)
const loading = ref(false)
const error = ref('')
const lastRefreshedAt = ref<Date | null>(null)
const secondsSinceRefresh = ref(0)
const expandedUsers = ref<Set<number>>(new Set())

const noAnalyserConfigured = computed(() => {
  if (!statusData.value) return false
  const analysers = statusData.value.modules.filter((m) => m.type === 'analyser')
  return !analysers.some((m) => m.enabled && m.configured)
})

const queuedCount = computed(() => {
  return statusData.value?.system.queue.queued ?? 0
})

const groupedModules = computed(() => {
  if (!statusData.value) return []
  const groups: { type: string; label: string; modules: ModuleEntry[] }[] = []
  const seen = new Map<string, { type: string; label: string; modules: ModuleEntry[] }>()
  for (const mod of statusData.value.modules) {
    let group = seen.get(mod.type)
    if (!group) {
      group = { type: mod.type, label: t(`system.moduleType.${mod.type}`), modules: [] }
      seen.set(mod.type, group)
      groups.push(group)
    }
    group.modules.push(mod)
  }
  return groups
})

let pollInterval: ReturnType<typeof setInterval> | null = null
let tickInterval: ReturnType<typeof setInterval> | null = null

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

// --- Module-level mode helpers (for header badges) ---

function moduleModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    active: t('system.llmActive'),
    idle: t('system.llmIdle'),
    polling: t('system.modePolling'),
    processing: t('system.modeProcessing'),
    connecting: t('system.modeConnecting'),
    error_backoff: t('system.modeStopped'),
    stopped: t('system.modeStopped'),
  }
  return labels[mode] || mode
}

function moduleModeColor(mode: string): string {
  const colors: Record<string, string> = {
    active: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-400',
    idle: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-400',
    polling: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-400',
    processing: 'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-400',
    connecting: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    error_backoff: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-400',
    stopped: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  }
  return colors[mode] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
}

function moduleModeDotColor(mode: string): string {
  const colors: Record<string, string> = {
    active: 'bg-blue-500',
    idle: 'bg-blue-500',
    polling: 'bg-blue-500',
    processing: 'bg-amber-500',
    connecting: 'bg-gray-400',
    error_backoff: 'bg-red-500',
    stopped: 'bg-gray-400',
  }
  return colors[mode] || 'bg-gray-400'
}

function emailUserFolderCount(status: EmailUserStatus): number {
  return status.users.reduce(
    (sum, user) => sum + user.accounts.reduce((aSum, account) => aSum + account.folders.length, 0),
    0,
  )
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
    const res = await api.get<StatusResponse>('/system/status')
    statusData.value = res.data

    lastRefreshedAt.value = new Date()
    secondsSinceRefresh.value = 0
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('system.loadFailed')
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await fetchStatus()
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
