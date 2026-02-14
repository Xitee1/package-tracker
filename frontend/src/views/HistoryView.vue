<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('history.title') }}</h1>
    </div>

    <!-- Filters -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6"
    >
      <div class="p-4">
        <div class="flex flex-col sm:flex-row gap-4">
          <!-- Account Dropdown -->
          <div class="sm:w-56">
            <select
              v-model="selectedAccountId"
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option :value="null">{{ t('history.allAccounts') }}</option>
              <option
                v-for="account in accountsStore.accounts"
                :key="account.id"
                :value="account.id"
              >
                {{ account.name }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Relevance Tabs -->
      <div class="border-t border-gray-200 dark:border-gray-700 px-4">
        <nav class="flex space-x-6 -mb-px" aria-label="Relevance filter">
          <button
            v-for="tab in relevanceTabs"
            :key="tab.value"
            @click="selectRelevanceTab(tab.value)"
            class="py-3 px-1 border-b-2 text-sm font-medium whitespace-nowrap"
            :class="
              activeRelevanceTab === tab.value
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500'
            "
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>
    </div>

    <!-- Table -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <!-- Loading -->
      <div
        v-if="scanHistoryStore.loading"
        class="p-8 text-center text-gray-500 dark:text-gray-400"
      >
        {{ t('common.loading') }}
      </div>

      <!-- Empty -->
      <div
        v-else-if="scanHistoryStore.scans.items.length === 0"
        class="p-8 text-center text-gray-500 dark:text-gray-400"
      >
        <p class="text-lg">{{ t('history.noResults') }}</p>
      </div>

      <!-- Table Content -->
      <div v-else class="overflow-x-auto">
        <!-- Desktop Table -->
        <table class="w-full hidden lg:table">
          <thead>
            <tr
              class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700"
            >
              <th class="px-5 py-3">{{ t('history.date') }}</th>
              <th class="px-5 py-3">{{ t('history.subject') }}</th>
              <th class="px-5 py-3">{{ t('history.sender') }}</th>
              <th class="px-5 py-3">{{ t('history.account') }}</th>
              <th class="px-5 py-3">{{ t('history.relevance') }}</th>
              <th class="px-5 py-3">{{ t('history.order') }}</th>
              <th class="px-5 py-3">{{ t('history.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="scan in scanHistoryStore.scans.items"
              :key="scan.id"
              class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                {{ formatDate(scan.email_date || scan.created_at) }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-900 dark:text-white max-w-xs truncate">
                {{ scan.subject }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                {{ scan.sender }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400">
                {{ scan.account_name || '-' }}
              </td>
              <td class="px-5 py-4">
                <span
                  v-if="scan.is_relevant"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400"
                >
                  {{ t('common.yes') }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                >
                  {{ t('common.no') }}
                </span>
              </td>
              <td class="px-5 py-4 text-sm">
                <router-link
                  v-if="scan.order_id"
                  :to="`/orders/${scan.order_id}`"
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {{ t('history.viewOrder') }}
                </router-link>
                <span v-else class="text-gray-400 dark:text-gray-500">-</span>
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    @click="openDetail(scan)"
                    class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    {{ t('history.viewDetail') }}
                  </button>
                  <span
                    v-if="scan.rescan_queued"
                    class="text-xs px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400"
                  >
                    {{ t('history.rescanQueued') }}
                  </span>
                  <button
                    v-else
                    @click="handleRescan(scan)"
                    class="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800"
                  >
                    {{ t('history.rescan') }}
                  </button>
                  <button
                    @click="handleDelete(scan)"
                    class="text-xs px-2 py-1 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800"
                  >
                    {{ t('common.delete') }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Mobile Cards -->
        <div class="lg:hidden divide-y divide-gray-200 dark:divide-gray-700">
          <div
            v-for="scan in scanHistoryStore.scans.items"
            :key="scan.id"
            class="p-4 space-y-2"
          >
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-900 dark:text-white truncate flex-1 mr-2">
                {{ scan.subject }}
              </span>
              <span
                v-if="scan.is_relevant"
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400 flex-shrink-0"
              >
                {{ t('common.yes') }}
              </span>
              <span
                v-else
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 flex-shrink-0"
              >
                {{ t('common.no') }}
              </span>
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">
              {{ scan.sender }} &mdash; {{ formatDate(scan.email_date || scan.created_at) }}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">
              {{ scan.account_name || '-' }}
            </div>
            <div class="flex items-center gap-2 pt-1">
              <button
                @click="openDetail(scan)"
                class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                {{ t('history.viewDetail') }}
              </button>
              <span
                v-if="scan.rescan_queued"
                class="text-xs px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400"
              >
                {{ t('history.rescanQueued') }}
              </span>
              <button
                v-else
                @click="handleRescan(scan)"
                class="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800"
              >
                {{ t('history.rescan') }}
              </button>
              <button
                @click="handleDelete(scan)"
                class="text-xs px-2 py-1 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800"
              >
                {{ t('common.delete') }}
              </button>
              <router-link
                v-if="scan.order_id"
                :to="`/orders/${scan.order_id}`"
                class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                {{ t('history.viewOrder') }}
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="totalPages > 1"
      class="flex items-center justify-between mt-4"
    >
      <p class="text-sm text-gray-600 dark:text-gray-400">
        {{ t('history.page', { page: currentPage, total: totalPages }) }}
      </p>
      <div class="flex gap-2">
        <button
          :disabled="currentPage <= 1"
          @click="goToPage(currentPage - 1)"
          class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ t('history.previous') }}
        </button>
        <button
          :disabled="currentPage >= totalPages"
          @click="goToPage(currentPage + 1)"
          class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ t('history.next') }}
        </button>
      </div>
    </div>

    <!-- Detail Modal -->
    <div
      v-if="detailScan"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/50" @click="closeDetail"></div>

      <!-- Modal Content -->
      <div
        class="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ t('history.detail') }}
          </h2>
          <button
            @click="closeDetail"
            class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="px-6 py-4 space-y-4">
          <!-- Subject -->
          <div>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              {{ t('history.subject') }}
            </p>
            <p class="text-sm text-gray-900 dark:text-white mt-1">{{ detailScan.subject }}</p>
          </div>

          <!-- Sender & Date -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('history.sender') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">{{ detailScan.sender }}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('history.date') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">
                {{ formatDate(detailScan.email_date || detailScan.created_at) }}
              </p>
            </div>
          </div>

          <!-- Account & Folder -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('history.account') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">
                {{ detailScan.account_name || '-' }}
              </p>
            </div>
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('history.folder') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">{{ detailScan.folder_path }}</p>
            </div>
          </div>

          <!-- Relevant & Order -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('history.relevance') }}
              </p>
              <div class="mt-1">
                <span
                  v-if="detailScan.is_relevant"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400"
                >
                  {{ t('common.yes') }}
                </span>
                <span
                  v-else
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                >
                  {{ t('common.no') }}
                </span>
              </div>
            </div>
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('history.order') }}
              </p>
              <div class="mt-1">
                <router-link
                  v-if="detailScan.order_id"
                  :to="`/orders/${detailScan.order_id}`"
                  class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  @click="closeDetail"
                >
                  {{ t('history.viewOrder') }}
                </router-link>
                <span v-else class="text-sm text-gray-400 dark:text-gray-500">-</span>
              </div>
            </div>
          </div>

          <!-- LLM Response -->
          <div v-if="detailScan.llm_raw_response">
            <button
              @click="llmResponseExpanded = !llmResponseExpanded"
              class="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase hover:text-gray-700 dark:hover:text-gray-300"
            >
              <svg
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-90': llmResponseExpanded }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
              {{ t('history.llmResponse') }}
            </button>
            <div v-if="llmResponseExpanded" class="mt-2">
              <pre
                class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md p-3 overflow-x-auto max-h-64 overflow-y-auto text-gray-800 dark:text-gray-200"
              >{{ JSON.stringify(detailScan.llm_raw_response, null, 2) }}</pre>
            </div>
          </div>

          <!-- Email Content -->
          <div>
            <div class="flex items-center gap-3">
              <button
                v-if="!emailContent && !emailLoading && !emailError"
                @click="handleFetchEmail"
                class="text-xs px-3 py-1.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                {{ t('history.fetchEmail') }}
              </button>
            </div>

            <div v-if="emailLoading" class="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {{ t('history.fetchingEmail') }}
            </div>

            <div
              v-if="emailError"
              class="mt-2 text-sm text-amber-600 dark:text-amber-400"
            >
              {{ t('history.emailNotAvailable') }}
            </div>

            <div v-if="emailContent" class="mt-2">
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase mb-1">
                {{ t('history.emailContent') }}
              </p>
              <pre
                class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md p-3 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap text-gray-800 dark:text-gray-200"
              >{{ emailContent.body_text }}</pre>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <span
              v-if="detailScan.rescan_queued"
              class="text-xs px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400"
            >
              {{ t('history.rescanQueued') }}
            </span>
            <button
              v-else
              @click="handleRescan(detailScan)"
              class="text-xs px-3 py-1.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800"
            >
              {{ t('history.rescan') }}
            </button>
            <button
              @click="closeDetail"
              class="text-xs px-3 py-1.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 ml-auto"
            >
              {{ t('history.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useScanHistoryStore, type EmailScan, type EmailContent } from '@/stores/scanHistory'
import { useAccountsStore } from '@/stores/accounts'

const { t } = useI18n()
const scanHistoryStore = useScanHistoryStore()
const accountsStore = useAccountsStore()

// --- Filter State ---
const selectedAccountId = ref<number | null>(null)
const activeRelevanceTab = ref<string>('all')
const currentPage = ref(1)

const relevanceTabs = computed(() => [
  { label: t('history.all'), value: 'all' },
  { label: t('history.relevant'), value: 'relevant' },
  { label: t('history.notRelevant'), value: 'not_relevant' },
])

const totalPages = computed(() => {
  const { total, per_page } = scanHistoryStore.scans
  return Math.max(1, Math.ceil(total / per_page))
})

// --- Detail Modal State ---
const detailScan = ref<EmailScan | null>(null)
const llmResponseExpanded = ref(false)
const emailContent = ref<EmailContent | null>(null)
const emailLoading = ref(false)
const emailError = ref(false)

// --- Data Fetching ---

function buildParams() {
  const params: Record<string, unknown> = {
    page: currentPage.value,
    per_page: 50,
  }
  if (selectedAccountId.value !== null) {
    params.account_id = selectedAccountId.value
  }
  if (activeRelevanceTab.value === 'relevant') {
    params.is_relevant = true
  } else if (activeRelevanceTab.value === 'not_relevant') {
    params.is_relevant = false
  }
  return params
}

async function loadScans() {
  await scanHistoryStore.fetchScans(buildParams())
}

function onFilterChange() {
  currentPage.value = 1
  loadScans()
}

function selectRelevanceTab(value: string) {
  activeRelevanceTab.value = value
  currentPage.value = 1
  loadScans()
}

function goToPage(page: number) {
  currentPage.value = page
  loadScans()
}

// --- Detail Modal ---

function openDetail(scan: EmailScan) {
  detailScan.value = scan
  llmResponseExpanded.value = false
  emailContent.value = null
  emailLoading.value = false
  emailError.value = false
}

function closeDetail() {
  detailScan.value = null
}

async function handleFetchEmail() {
  if (!detailScan.value) return
  emailLoading.value = true
  emailError.value = false
  try {
    emailContent.value = await scanHistoryStore.fetchEmailContent(detailScan.value.id)
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 404) {
      emailError.value = true
    } else {
      emailError.value = true
    }
  } finally {
    emailLoading.value = false
  }
}

// --- Actions ---

async function handleRescan(scan: EmailScan) {
  try {
    const updated = await scanHistoryStore.queueRescan(scan.id)
    // Update the item in the local list
    const idx = scanHistoryStore.scans.items.findIndex((s) => s.id === scan.id)
    if (idx !== -1) {
      scanHistoryStore.scans.items[idx] = updated
    }
    // Update detail if open
    if (detailScan.value?.id === scan.id) {
      detailScan.value = updated
    }
  } catch {
    alert(t('history.rescanFailed'))
  }
}

async function handleDelete(scan: EmailScan) {
  if (!window.confirm(t('history.confirmDelete'))) return
  try {
    await scanHistoryStore.deleteScan(scan.id)
    await loadScans()
    if (detailScan.value?.id === scan.id) {
      closeDetail()
    }
  } catch {
    alert(t('history.deleteFailed'))
  }
}

// --- Formatting ---

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return (
    date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) +
    ' ' +
    date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  )
}

// --- Lifecycle ---

onMounted(() => {
  accountsStore.fetchAccounts()
  loadScans()
})
</script>
