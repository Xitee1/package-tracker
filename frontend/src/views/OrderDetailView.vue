<template>
  <div>
    <!-- Back link -->
    <div class="mb-6">
      <router-link
        to="/orders"
        class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
        {{ $t('orderDetail.backToOrders') }}
      </router-link>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ $t('orderDetail.loadingDetails') }}
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/30 dark:border-red-800 dark:text-red-400 px-4 py-3 rounded-md"
    >
      {{ error }}
    </div>

    <!-- Order Detail -->
    <template v-else-if="order">
      <!-- Header -->
      <div class="flex items-start justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ $t('orderDetail.orderTitle', { id: order.order_number || '#' + order.id }) }}
          </h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">
            {{ $t('orderDetail.created', { date: formatDate(order.created_at) }) }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="showEditModal = true"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:text-gray-300 dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {{ $t('common.edit') }}
          </button>
          <button
            @click="showDeleteConfirm = true"
            class="px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50 dark:text-red-400 dark:bg-gray-800 dark:border-red-700 dark:hover:bg-red-900/30 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {{ $t('common.delete') }}
          </button>
        </div>
      </div>

      <!-- Status Badge -->
      <div class="mb-6">
        <StatusBadge :status="order.status" />
      </div>

      <!-- Order Info Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <!-- Order Details Card -->
        <div
          class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
        >
          <h3
            class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4"
          >
            {{ $t('orderDetail.orderDetails') }}
          </h3>

          <dl class="space-y-3">
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.orderNumber') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ order.order_number || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.vendor') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ order.vendor_name || order.vendor_domain || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.orderDate') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ order.order_date ? formatDate(order.order_date) : '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.totalAmount') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ formatAmount(order.total_amount, order.currency) }}
                </dd>
              </div>
            </dl>
        </div>

        <!-- Shipping Details Card -->
        <div
          class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5"
        >
          <h3
            class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4"
          >
            {{ $t('orderDetail.shippingDetails') }}
          </h3>

          <dl class="space-y-3">
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.trackingNumber') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ order.tracking_number || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.carrier') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ order.carrier || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {{ $t('orderDetail.estimatedDelivery') }}
                </dt>
                <dd class="text-sm text-gray-900 dark:text-white mt-0.5">
                  {{ order.estimated_delivery ? formatDate(order.estimated_delivery) : '-' }}
                </dd>
              </div>
            </dl>
        </div>
      </div>

      <!-- Items -->
      <div
        v-if="order.items && order.items.length > 0"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-8"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
            {{ $t('orderDetail.items') }}
          </h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr
                class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700"
              >
                <th class="px-5 py-3">{{ $t('orderDetail.item') }}</th>
                <th class="px-5 py-3">{{ $t('orderDetail.qty') }}</th>
                <th class="px-5 py-3 text-right">{{ $t('orderDetail.price') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr v-for="(item, idx) in order.items" :key="idx">
                <td class="px-5 py-3 text-sm text-gray-900 dark:text-white">{{ item.name }}</td>
                <td class="px-5 py-3 text-sm text-gray-600 dark:text-gray-400">
                  {{ item.quantity }}
                </td>
                <td class="px-5 py-3 text-sm text-gray-600 dark:text-gray-400 text-right">
                  {{ item.price !== null ? formatAmount(item.price, order.currency) : '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- State Timeline -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
            {{ $t('orderDetail.stateTimeline') }}
          </h3>
        </div>

        <div
          v-if="order.states.length === 0"
          class="p-8 text-center text-gray-500 dark:text-gray-400 text-sm"
        >
          {{ $t('orderDetail.noStates') }}
        </div>

        <div v-else class="p-5">
          <div class="relative">
            <div class="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700"></div>

            <div
              v-for="(state, idx) in sortedStates"
              :key="state.id"
              class="relative flex gap-4 pb-6 last:pb-0"
            >
              <div
                class="relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                :class="
                  idx === 0 ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-gray-100 dark:bg-gray-800'
                "
              >
                <div
                  class="w-2.5 h-2.5 rounded-full"
                  :class="idx === 0 ? 'bg-blue-600' : 'bg-gray-400 dark:bg-gray-500'"
                ></div>
              </div>
              <div class="flex-1 min-w-0 pt-1">
                <div class="flex items-center gap-2">
                  <StatusBadge :status="state.status" />
                </div>
                <p
                  v-if="state.source_type || state.source_info"
                  class="text-sm text-gray-600 dark:text-gray-400 mt-0.5"
                >
                  <span v-if="state.source_type" class="font-medium">{{ state.source_type }}</span>
                  <span v-if="state.source_info"> &mdash; {{ state.source_info }}</span>
                </p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  {{ formatDateTime(state.created_at) }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="fixed inset-0 bg-black/50" @click="showDeleteConfirm = false"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {{ $t('orderDetail.deleteOrder') }}
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
          {{ $t('orderDetail.deleteConfirm') }}
        </p>
        <div class="flex justify-end gap-2">
          <button
            @click="showDeleteConfirm = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:text-gray-300 dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            @click="confirmDelete"
            :disabled="deleting"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {{ deleting ? $t('common.deleting') : $t('common.delete') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit Order Modal -->
    <OrderFormModal
      v-if="showEditModal && order"
      mode="edit"
      :order="order"
      @close="showEditModal = false"
      @saved="onOrderSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useOrdersStore, type OrderDetail } from '@/stores/orders'
import StatusBadge from '@/components/StatusBadge.vue'
import OrderFormModal from '@/components/OrderFormModal.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const ordersStore = useOrdersStore()

const order = ref<OrderDetail | null>(null)
const loading = ref(true)
const error = ref('')
const showEditModal = ref(false)
const showDeleteConfirm = ref(false)
const deleting = ref(false)

const sortedStates = computed(() => {
  if (!order.value) return []
  return [...order.value.states].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

async function onOrderSaved(id: number) {
  showEditModal.value = false
  order.value = await ordersStore.fetchOrder(id)
}

async function confirmDelete() {
  if (!order.value) return
  deleting.value = true
  try {
    await ordersStore.deleteOrder(order.value.id)
    router.push('/orders')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('orderDetail.deleteFailed')
    showDeleteConfirm.value = false
  } finally {
    deleting.value = false
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatAmount(amount: number | null, currency: string | null): string {
  if (amount === null) return '-'
  const curr = currency || 'USD'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: curr }).format(amount)
}

onMounted(async () => {
  const id = Number(route.params.id)
  if (isNaN(id)) {
    error.value = t('orderDetail.invalidOrderId')
    loading.value = false
    return
  }

  try {
    order.value = await ordersStore.fetchOrder(id)
  } catch {
    error.value = t('orderDetail.orderNotFound')
  } finally {
    loading.value = false
  }
})
</script>
