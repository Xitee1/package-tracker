<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('dashboard.title') }}
    </h1>

    <!-- Status Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
              {{ $t('dashboard.ordered') }}
            </p>
            <p class="text-2xl font-bold text-blue-600 mt-1">{{ statusCounts.ordered }}</p>
          </div>
          <div
            class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center"
          >
            <svg
              class="w-5 h-5 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
              />
            </svg>
          </div>
        </div>
      </div>

      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
              {{ $t('dashboard.shipped') }}
            </p>
            <p class="text-2xl font-bold text-indigo-600 mt-1">{{ statusCounts.shipped }}</p>
          </div>
          <div
            class="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center"
          >
            <svg
              class="w-5 h-5 text-indigo-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
          </div>
        </div>
      </div>

      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
              {{ $t('dashboard.inTransit') }}
            </p>
            <p class="text-2xl font-bold text-orange-600 mt-1">{{ statusCounts.in_transit }}</p>
          </div>
          <div
            class="w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/40 flex items-center justify-center"
          >
            <svg
              class="w-5 h-5 text-orange-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"
              />
            </svg>
          </div>
        </div>
      </div>

      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
              {{ $t('dashboard.delivered') }}
            </p>
            <p class="text-2xl font-bold text-green-600 mt-1">{{ statusCounts.delivered }}</p>
          </div>
          <div
            class="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center"
          >
            <svg
              class="w-5 h-5 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Orders -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <div
        class="px-5 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between"
      >
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
          {{ $t('dashboard.recentOrders') }}
        </h2>
        <router-link
          to="/orders"
          class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
        >
          {{ $t('dashboard.viewAll') }}
        </router-link>
      </div>

      <div v-if="ordersStore.loading" class="p-8 text-center text-gray-500 dark:text-gray-400">
        {{ $t('dashboard.loadingOrders') }}
      </div>

      <div
        v-else-if="recentOrders.length === 0"
        class="p-8 text-center text-gray-500 dark:text-gray-400"
      >
        {{ $t('dashboard.noOrders') }}
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr
              class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
            >
              <th class="px-5 py-3">{{ $t('dashboard.order') }}</th>
              <th class="px-5 py-3">{{ $t('dashboard.vendor') }}</th>
              <th class="px-5 py-3">{{ $t('dashboard.status') }}</th>
              <th class="px-5 py-3">{{ $t('dashboard.date') }}</th>
              <th class="px-5 py-3">{{ $t('dashboard.amount') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="order in recentOrders"
              :key="order.id"
              @click="$router.push(`/orders/${order.id}`)"
              class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
            >
              <td class="px-5 py-3">
                <div class="text-sm font-medium text-gray-900 dark:text-white">
                  {{ order.order_number || order.tracking_number || `#${order.id}` }}
                </div>
                <div
                  v-if="order.tracking_number && order.order_number"
                  class="text-xs text-gray-500 dark:text-gray-400"
                >
                  {{ order.tracking_number }}
                </div>
              </td>
              <td class="px-5 py-3 text-sm text-gray-600 dark:text-gray-400">
                {{ order.vendor_name || order.vendor_domain || '-' }}
              </td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :class="statusClass(order.status)"
                >
                  {{ formatStatus(order.status) }}
                </span>
              </td>
              <td class="px-5 py-3 text-sm text-gray-600 dark:text-gray-400">
                {{ formatDate(order.order_date || order.created_at) }}
              </td>
              <td class="px-5 py-3 text-sm text-gray-600 dark:text-gray-400">
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
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdersStore } from '@/stores/orders'
import { formatDate, formatAmount } from '@/utils/format'

const { t, te } = useI18n()
const ordersStore = useOrdersStore()

const statusCounts = computed(() => {
  const counts = { ordered: 0, shipped: 0, in_transit: 0, delivered: 0 }
  for (const order of ordersStore.orders) {
    if (order.status === 'ordered') counts.ordered++
    else if (order.status === 'shipped' || order.status === 'shipment_preparing') counts.shipped++
    else if (order.status === 'in_transit' || order.status === 'out_for_delivery')
      counts.in_transit++
    else if (order.status === 'delivered') counts.delivered++
  }
  return counts
})

const recentOrders = computed(() => {
  return [...ordersStore.orders]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 10)
})

function statusClass(status: string): string {
  const classes: Record<string, string> = {
    ordered: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    shipment_preparing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    shipped: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
    in_transit: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    out_for_delivery: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
    delivered: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  }
  return classes[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
}

function formatStatus(status: string): string {
  const key = `status.${status}`
  if (te(key)) return t(key)
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

onMounted(() => {
  ordersStore.fetchOrders()
})
</script>
