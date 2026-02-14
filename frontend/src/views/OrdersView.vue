<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('orders.title') }}</h1>
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
                @input="debouncedSearch"
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
        v-else-if="filteredOrders.length === 0"
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
              <th class="px-5 py-3">{{ $t('orders.order') }}</th>
              <th class="px-5 py-3">{{ $t('orders.vendor') }}</th>
              <th class="px-5 py-3">{{ $t('orders.carrier') }}</th>
              <th class="px-5 py-3">{{ $t('orders.status') }}</th>
              <th class="px-5 py-3">{{ $t('orders.date') }}</th>
              <th class="px-5 py-3 text-right">{{ $t('orders.amount') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="order in filteredOrders"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdersStore } from '@/stores/orders'
import StatusBadge from '@/components/StatusBadge.vue'

const { t } = useI18n()
const ordersStore = useOrdersStore()

const searchQuery = ref('')
const activeTab = ref('')

const tabs = computed(() => {
  const all = ordersStore.orders.length
  const ordered = ordersStore.orders.filter((o) => o.status === 'ordered').length
  const shipped = ordersStore.orders.filter(
    (o) => o.status === 'shipped' || o.status === 'shipment_preparing',
  ).length
  const inTransit = ordersStore.orders.filter(
    (o) => o.status === 'in_transit' || o.status === 'out_for_delivery',
  ).length
  const delivered = ordersStore.orders.filter((o) => o.status === 'delivered').length

  return [
    { label: t('orders.all'), value: '', count: all },
    { label: t('orders.ordered'), value: 'ordered', count: ordered },
    { label: t('orders.shipped'), value: 'shipped', count: shipped },
    { label: t('orders.inTransit'), value: 'in_transit', count: inTransit },
    { label: t('orders.delivered'), value: 'delivered', count: delivered },
  ]
})

const filteredOrders = computed(() => {
  let result = ordersStore.orders

  if (activeTab.value) {
    result = result.filter((o) => {
      if (activeTab.value === 'shipped')
        return o.status === 'shipped' || o.status === 'shipment_preparing'
      if (activeTab.value === 'in_transit')
        return o.status === 'in_transit' || o.status === 'out_for_delivery'
      return o.status === activeTab.value
    })
  }

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (o) =>
        o.order_number?.toLowerCase().includes(q) ||
        o.tracking_number?.toLowerCase().includes(q) ||
        o.vendor_name?.toLowerCase().includes(q) ||
        o.vendor_domain?.toLowerCase().includes(q) ||
        o.carrier?.toLowerCase().includes(q),
    )
  }

  return [...result].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function debouncedSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    // Client-side filtering is already reactive via computed
  }, 300)
}

function selectTab(value: string) {
  activeTab.value = value
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
  ordersStore.fetchOrders()
})
</script>
