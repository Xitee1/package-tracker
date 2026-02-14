<template>
  <div class="p-6 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('queue.title') }}</h1>
    </div>

    <!-- Filters -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6"
    >
      <div class="p-4">
        <div class="flex flex-col sm:flex-row gap-4">
          <!-- Status Dropdown -->
          <div class="sm:w-56">
            <select
              v-model="selectedStatus"
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">{{ t('queue.allStatuses') }}</option>
              <option value="queued">{{ t('queue.statusQueued') }}</option>
              <option value="processing">{{ t('queue.statusProcessing') }}</option>
              <option value="completed">{{ t('queue.statusCompleted') }}</option>
              <option value="failed">{{ t('queue.statusFailed') }}</option>
            </select>
          </div>

          <!-- Source Type Dropdown -->
          <div class="sm:w-56">
            <select
              v-model="selectedSourceType"
              @change="onFilterChange"
              class="w-full px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">{{ t('queue.allSourceTypes') }}</option>
              <option value="email">IMAP</option>
              <option value="manual">{{ t('queue.sourceManual') }}</option>
              <option value="api">API</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <!-- Loading -->
      <div v-if="queueStore.loading" class="p-8 text-center text-gray-500 dark:text-gray-400">
        {{ t('common.loading') }}
      </div>

      <!-- Empty -->
      <div
        v-else-if="queueStore.items.items.length === 0"
        class="p-8 text-center text-gray-500 dark:text-gray-400"
      >
        <p class="text-lg">{{ t('queue.noResults') }}</p>
      </div>

      <!-- Table Content -->
      <div v-else class="overflow-x-auto">
        <!-- Desktop Table -->
        <table class="w-full hidden lg:table">
          <thead>
            <tr
              class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700"
            >
              <th class="px-5 py-3">{{ t('queue.date') }}</th>
              <th class="px-5 py-3">{{ t('queue.sourceType') }}</th>
              <th class="px-5 py-3">{{ t('queue.sourceInfo') }}</th>
              <th class="px-5 py-3">{{ t('queue.status') }}</th>
              <th class="px-5 py-3">{{ t('queue.order') }}</th>
              <th class="px-5 py-3">{{ t('queue.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="item in queueStore.items.items"
              :key="item.id"
              class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
                {{ formatDate(item.created_at) }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400">
                {{ item.source_type }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                {{ item.source_info }}
              </td>
              <td class="px-5 py-4">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="statusBadgeClass(item.status)"
                >
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td class="px-5 py-4 text-sm">
                <router-link
                  v-if="item.order_id"
                  :to="`/orders/${item.order_id}`"
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {{ t('queue.viewOrder') }}
                </router-link>
                <span v-else class="text-gray-400 dark:text-gray-500">-</span>
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    @click="openDetail(item)"
                    class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    {{ t('queue.viewDetail') }}
                  </button>
                  <button
                    @click="handleRetry(item)"
                    class="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800"
                  >
                    {{ t('queue.retry') }}
                  </button>
                  <button
                    @click="handleDelete(item)"
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
          <div v-for="item in queueStore.items.items" :key="item.id" class="p-4 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-900 dark:text-white truncate flex-1 mr-2">
                {{ item.source_info }}
              </span>
              <span
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0"
                :class="statusBadgeClass(item.status)"
              >
                {{ statusLabel(item.status) }}
              </span>
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400">
              {{ item.source_type }} &mdash; {{ formatDate(item.created_at) }}
            </div>
            <div class="flex items-center gap-2 pt-1">
              <button
                @click="openDetail(item)"
                class="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                {{ t('queue.viewDetail') }}
              </button>
              <button
                @click="handleRetry(item)"
                class="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800"
              >
                {{ t('queue.retry') }}
              </button>
              <button
                @click="handleDelete(item)"
                class="text-xs px-2 py-1 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-800"
              >
                {{ t('common.delete') }}
              </button>
              <router-link
                v-if="item.order_id"
                :to="`/orders/${item.order_id}`"
                class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                {{ t('queue.viewOrder') }}
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-between mt-4">
      <p class="text-sm text-gray-600 dark:text-gray-400">
        {{ t('queue.page', { page: currentPage, total: totalPages }) }}
      </p>
      <div class="flex gap-2">
        <button
          :disabled="currentPage <= 1"
          @click="goToPage(currentPage - 1)"
          class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ t('queue.previous') }}
        </button>
        <button
          :disabled="currentPage >= totalPages"
          @click="goToPage(currentPage + 1)"
          class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ t('queue.next') }}
        </button>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="detailItem" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/50" @click="closeDetail"></div>

      <!-- Modal Content -->
      <div
        class="relative bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <div
          class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between"
        >
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ t('queue.detail') }}
          </h2>
          <button
            @click="closeDetail"
            class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div class="px-6 py-4 space-y-4">
          <!-- Source Type & Source Info -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('queue.sourceType') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">{{ detailItem.source_type }}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('queue.sourceInfo') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">{{ detailItem.source_info }}</p>
            </div>
          </div>

          <!-- Status & Date -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('queue.status') }}
              </p>
              <div class="mt-1">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="statusBadgeClass(detailItem.status)"
                >
                  {{ statusLabel(detailItem.status) }}
                </span>
              </div>
            </div>
            <div>
              <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                {{ t('queue.date') }}
              </p>
              <p class="text-sm text-gray-900 dark:text-white mt-1">
                {{ formatDate(detailItem.created_at) }}
              </p>
            </div>
          </div>

          <!-- Order -->
          <div>
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              {{ t('queue.order') }}
            </p>
            <div class="mt-1">
              <router-link
                v-if="detailItem.order_id"
                :to="`/orders/${detailItem.order_id}`"
                class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                @click="closeDetail"
              >
                {{ t('queue.viewOrder') }}
              </router-link>
              <span v-else class="text-sm text-gray-400 dark:text-gray-500">-</span>
            </div>
          </div>

          <!-- Tabs: Raw Data / Extracted Data / Error -->
          <div>
            <nav
              class="flex space-x-4 border-b border-gray-200 dark:border-gray-700 -mb-px"
              aria-label="Detail tabs"
            >
              <button
                @click="detailTab = 'raw'"
                class="py-2 px-1 border-b-2 text-sm font-medium whitespace-nowrap"
                :class="
                  detailTab === 'raw'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500'
                "
              >
                {{ t('queue.rawData') }}
              </button>
              <button
                @click="detailTab = 'extracted'"
                class="py-2 px-1 border-b-2 text-sm font-medium whitespace-nowrap"
                :class="
                  detailTab === 'extracted'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500'
                "
              >
                {{ t('queue.extractedData') }}
              </button>
              <button
                v-if="detailItem.status === 'failed'"
                @click="detailTab = 'error'"
                class="py-2 px-1 border-b-2 text-sm font-medium whitespace-nowrap"
                :class="
                  detailTab === 'error'
                    ? 'border-red-500 text-red-600 dark:text-red-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500'
                "
              >
                {{ t('queue.error') }}
              </button>
            </nav>

            <div class="mt-3">
              <!-- Raw Data Tab -->
              <div v-if="detailTab === 'raw'">
                <pre
                  class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md p-3 overflow-x-auto max-h-64 overflow-y-auto text-gray-800 dark:text-gray-200"
                  >{{ JSON.stringify(detailItem.raw_data, null, 2) }}</pre
                >
              </div>

              <!-- Extracted Data Tab -->
              <div v-if="detailTab === 'extracted'">
                <div v-if="detailItem.extracted_data">
                  <pre
                    class="text-xs bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md p-3 overflow-x-auto max-h-64 overflow-y-auto text-gray-800 dark:text-gray-200"
                    >{{ JSON.stringify(detailItem.extracted_data, null, 2) }}</pre
                  >
                </div>
                <p v-else class="text-sm text-gray-400 dark:text-gray-500">
                  {{ t('queue.noExtractedData') }}
                </p>
              </div>

              <!-- Error Tab -->
              <div v-if="detailTab === 'error'">
                <div
                  v-if="detailItem.error_message"
                  class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3"
                >
                  {{ detailItem.error_message }}
                </div>
                <p v-else class="text-sm text-gray-400 dark:text-gray-500">
                  {{ t('queue.noError') }}
                </p>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="handleRetry(detailItem)"
              class="text-xs px-3 py-1.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-800"
            >
              {{ t('queue.retry') }}
            </button>
            <button
              @click="closeDetail"
              class="text-xs px-3 py-1.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 ml-auto"
            >
              {{ t('queue.close') }}
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
import { useQueueStore, type QueueItem } from '@/stores/queue'

const { t } = useI18n()
const queueStore = useQueueStore()

// --- Filter State ---
const selectedStatus = ref<string>('')
const selectedSourceType = ref<string>('')
const currentPage = ref(1)

const totalPages = computed(() => {
  const { total, per_page } = queueStore.items
  return Math.max(1, Math.ceil(total / per_page))
})

// --- Detail Modal State ---
const detailItem = ref<QueueItem | null>(null)
const detailTab = ref<'raw' | 'extracted' | 'error'>('raw')

// --- Data Fetching ---

function buildParams() {
  const params: Record<string, unknown> = {
    page: currentPage.value,
    per_page: 50,
  }
  if (selectedStatus.value) {
    params.status = selectedStatus.value
  }
  if (selectedSourceType.value) {
    params.source_type = selectedSourceType.value
  }
  return params
}

async function loadItems() {
  await queueStore.fetchItems(buildParams())
}

function onFilterChange() {
  currentPage.value = 1
  loadItems()
}

function goToPage(page: number) {
  currentPage.value = page
  loadItems()
}

// --- Detail Modal ---

function openDetail(item: QueueItem) {
  detailItem.value = item
  detailTab.value = 'raw'
}

function closeDetail() {
  detailItem.value = null
}

// --- Actions ---

async function handleRetry(item: QueueItem) {
  try {
    await queueStore.retryItem(item.id)
    await loadItems()
  } catch {
    alert(t('queue.retryFailed'))
  }
}

async function handleDelete(item: QueueItem) {
  if (!window.confirm(t('queue.confirmDelete'))) return
  try {
    await queueStore.deleteItem(item.id)
    await loadItems()
    if (detailItem.value?.id === item.id) {
      closeDetail()
    }
  } catch {
    alert(t('queue.deleteFailed'))
  }
}

// --- Status Badge ---

function statusBadgeClass(status: string): string {
  const classes: Record<string, string> = {
    queued: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    processing: 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-400',
    completed: 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400',
    failed: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-400',
  }
  return classes[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: t('queue.statusQueued'),
    processing: t('queue.statusProcessing'),
    completed: t('queue.statusCompleted'),
    failed: t('queue.statusFailed'),
  }
  return labels[status] || status
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
  loadItems()
})
</script>
