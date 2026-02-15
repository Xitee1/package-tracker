<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('orders.title') }}</h1>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        + {{ $t('orders.newOrder') }}
      </button>
    </div>

    <!-- Search and Filters -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6"
    >
      <div class="p-4">
        <div class="flex flex-col sm:flex-row gap-4">
          <!-- Search -->
          <div class="flex-1">
            <div class="relative">
              <svg
                class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                v-model="searchQuery"
                type="text"
                :placeholder="$t('orders.searchPlaceholder')"
                class="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Status Tabs -->
      <div class="border-t border-gray-200 dark:border-gray-700 px-4">
        <nav class="flex space-x-6 -mb-px" aria-label="Status filter">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            @click="selectTab(tab.value)"
            class="py-3 px-1 border-b-2 text-sm font-medium whitespace-nowrap"
            :class="
              activeTab === tab.value
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500'
            "
          >
            {{ tab.label }}
            <span
              v-if="tab.count > 0"
              class="ml-1.5 py-0.5 px-2 rounded-full text-xs"
              :class="
                activeTab === tab.value
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400'
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
              "
            >
              {{ tab.count }}
            </span>
          </button>
        </nav>
      </div>
    </div>

    <!-- Orders Table -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <div v-if="ordersStore.loading" class="p-8 text-center text-gray-500 dark:text-gray-400">
        {{ $t('orders.loadingOrders') }}
      </div>

      <div
        v-else-if="ordersStore.orders.length === 0"
        class="p-8 text-center text-gray-500 dark:text-gray-400"
      >
        <p class="text-lg mb-1">{{ $t('orders.noOrdersFound') }}</p>
        <p class="text-sm">{{ $t('orders.noOrdersHint') }}</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr
              class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700"
            >
              <th
                v-for="col in [
                  { key: 'order', label: $t('orders.order') },
                  { key: 'vendor', label: $t('orders.vendor') },
                  { key: 'carrier', label: $t('orders.carrier') },
                  { key: 'status', label: $t('orders.status') },
                  { key: 'date', label: $t('orders.date') },
                  { key: 'amount', label: $t('orders.amount') },
                ]"
                :key="col.key"
                @click="toggleSort(col.key)"
                class="px-5 py-3 cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                :class="{ 'text-right': col.key === 'amount' }"
              >
                <span class="inline-flex items-center gap-1">
                  {{ col.label }}
                  <svg
                    v-if="ordersStore.sortBy === SORT_COLUMN_MAP[col.key]"
                    class="w-3.5 h-3.5 text-blue-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    :aria-label="
                      ordersStore.sortDir === 'asc' ? $t('orders.sortAsc') : $t('orders.sortDesc')
                    "
                  >
                    <path
                      v-if="ordersStore.sortDir === 'asc'"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 15l7-7 7 7"
                    />
                    <path
                      v-else
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="order in ordersStore.orders"
              :key="order.id"
              @click="$router.push(`/orders/${order.id}`)"
              class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
            >
              <td class="px-5 py-4">
                <div class="text-sm font-medium text-gray-900 dark:text-white">
                  {{ order.order_number || `#${order.id}` }}
                </div>
                <div
                  v-if="order.tracking_number"
                  class="text-xs text-gray-500 dark:text-gray-400 mt-0.5"
                >
                  {{ order.tracking_number }}
                </div>
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400">
                {{ order.vendor_name || order.vendor_domain || '-' }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400">
                {{ order.carrier || '-' }}
              </td>
              <td class="px-5 py-4">
                <StatusBadge :status="order.status" />
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400">
                {{ formatDate(order.order_date || order.created_at) }}
              </td>
              <td class="px-5 py-4 text-sm text-gray-600 dark:text-gray-400 text-right">
                {{ formatAmount(order.total_amount, order.currency) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="ordersStore.total > ordersStore.perPage"
      class="flex items-center justify-between mt-4 px-1"
    >
      <button
        @click="prevPage"
        :disabled="ordersStore.page <= 1"
        class="px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ $t('orders.previousPage') }}
      </button>
      <span class="text-sm text-gray-600 dark:text-gray-400">
        {{ $t('orders.pageInfo', { page: ordersStore.page, totalPages }) }}
      </span>
      <button
        @click="nextPage"
        :disabled="ordersStore.page >= totalPages"
        class="px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ $t('orders.nextPage') }}
      </button>
    </div>

    <!-- Create Order Modal -->
    <OrderFormModal
      v-if="showCreateModal"
      mode="create"
      @close="showCreateModal = false"
      @saved="onOrderCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdersStore } from '@/stores/orders'
import StatusBadge from '@/components/StatusBadge.vue'
import OrderFormModal from '@/components/OrderFormModal.vue'

const { t } = useI18n()
const ordersStore = useOrdersStore()

const searchQuery = ref('')
const activeTab = ref('')
const showCreateModal = ref(false)

// Map tab values to comma-separated backend status params
const STATUS_MAP: Record<string, string> = {
  '': '',
  ordered: 'ordered',
  shipped: 'shipped,shipment_preparing',
  in_transit: 'in_transit,out_for_delivery',
  delivered: 'delivered',
}

const SORT_COLUMN_MAP: Record<string, string> = {
  order: 'order_number',
  vendor: 'vendor_name',
  carrier: 'carrier',
  status: 'status',
  date: 'order_date',
  amount: 'total_amount',
}

const tabs = computed(() => {
  const c = ordersStore.counts
  return [
    { label: t('orders.all'), value: '', count: c.total },
    { label: t('orders.ordered'), value: 'ordered', count: c.ordered },
    { label: t('orders.shipped'), value: 'shipped', count: c.shipped + c.shipment_preparing },
    { label: t('orders.inTransit'), value: 'in_transit', count: c.in_transit + c.out_for_delivery },
    { label: t('orders.delivered'), value: 'delivered', count: c.delivered },
  ]
})

const totalPages = computed(() => Math.max(1, Math.ceil(ordersStore.total / ordersStore.perPage)))

function buildParams() {
  const params: Record<string, string | number> = {
    page: ordersStore.page,
    per_page: ordersStore.perPage,
    sort_by: ordersStore.sortBy,
    sort_dir: ordersStore.sortDir,
  }
  const status = STATUS_MAP[activeTab.value]
  if (status) params.status = status
  if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
  return params
}

async function loadOrders() {
  await ordersStore.fetchOrders(buildParams())
}

async function loadCounts() {
  const search = searchQuery.value.trim()
  await ordersStore.fetchCounts(search ? { search } : undefined)
}

// Debounced search
let searchTimeout: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    ordersStore.page = 1
    loadOrders()
    loadCounts()
  }, 300)
})

function selectTab(value: string) {
  activeTab.value = value
  ordersStore.page = 1
  ordersStore.sortBy = 'order_date'
  ordersStore.sortDir = 'desc'
  loadOrders()
}

function toggleSort(column: string) {
  const backendColumn = SORT_COLUMN_MAP[column]
  if (!backendColumn) return
  if (ordersStore.sortBy === backendColumn) {
    ordersStore.sortDir = ordersStore.sortDir === 'asc' ? 'desc' : 'asc'
  } else {
    ordersStore.sortBy = backendColumn
    ordersStore.sortDir = 'desc'
  }
  ordersStore.page = 1
  loadOrders()
}

function prevPage() {
  if (ordersStore.page > 1) {
    ordersStore.page--
    loadOrders()
  }
}

function nextPage() {
  if (ordersStore.page < totalPages.value) {
    ordersStore.page++
    loadOrders()
  }
}

function onOrderCreated(_id: number) {
  showCreateModal.value = false
  ordersStore.page = 1
  loadOrders()
  loadCounts()
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatAmount(amount: number | null, currency: string | null): string {
  if (amount === null) return '-'
  const curr = currency || 'USD'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: curr }).format(amount)
}

onMounted(() => {
  loadOrders()
  loadCounts()
})
</script>
