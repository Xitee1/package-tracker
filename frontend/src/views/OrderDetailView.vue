<template>
  <div class="p-6 max-w-4xl mx-auto">
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
            v-if="!editing"
            @click="startEditing"
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

          <template v-if="editing">
            <div class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.orderNumber')
                }}</label>
                <input
                  v-model="editForm.order_number"
                  type="text"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.status')
                }}</label>
                <select
                  v-model="editForm.status"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ordered">{{ $t('orderDetail.statusOrdered') }}</option>
                  <option value="shipment_preparing">
                    {{ $t('orderDetail.statusShipmentPreparing') }}
                  </option>
                  <option value="shipped">{{ $t('orderDetail.statusShipped') }}</option>
                  <option value="in_transit">{{ $t('orderDetail.statusInTransit') }}</option>
                  <option value="out_for_delivery">
                    {{ $t('orderDetail.statusOutForDelivery') }}
                  </option>
                  <option value="delivered">{{ $t('orderDetail.statusDelivered') }}</option>
                </select>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.vendor')
                }}</label>
                <input
                  v-model="editForm.vendor_name"
                  type="text"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.orderDate')
                }}</label>
                <input
                  v-model="editForm.order_date"
                  type="date"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </template>

          <template v-else>
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
          </template>
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

          <template v-if="editing">
            <div class="space-y-3">
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.trackingNumber')
                }}</label>
                <input
                  v-model="editForm.tracking_number"
                  type="text"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.carrier')
                }}</label>
                <input
                  v-model="editForm.carrier"
                  type="text"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{
                  $t('orderDetail.estimatedDelivery')
                }}</label>
                <input
                  v-model="editForm.estimated_delivery"
                  type="date"
                  class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div class="flex gap-2 mt-5">
              <button
                @click="saveEdit"
                :disabled="saving"
                class="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {{ saving ? $t('common.saving') : $t('orderDetail.saveChanges') }}
              </button>
              <button
                @click="cancelEditing"
                class="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:text-gray-300 dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700"
              >
                {{ $t('common.cancel') }}
              </button>
            </div>
          </template>

          <template v-else>
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
          </template>
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

      <!-- Event Timeline -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
      >
        <div class="px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider">
            {{ $t('orderDetail.eventTimeline') }}
          </h3>
        </div>

        <div
          v-if="order.events.length === 0"
          class="p-8 text-center text-gray-500 dark:text-gray-400 text-sm"
        >
          {{ $t('orderDetail.noEvents') }}
        </div>

        <div v-else class="p-5">
          <div class="relative">
            <div class="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700"></div>

            <div
              v-for="(event, idx) in sortedEvents"
              :key="event.id"
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
                <p class="text-sm font-medium text-gray-900 dark:text-white">
                  {{ formatEventType(event.event_type) }}
                </p>
                <p v-if="event.description" class="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                  {{ event.description }}
                </p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  {{ formatDateTime(event.timestamp) }}
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useOrdersStore, type OrderDetail } from '@/stores/orders'
import StatusBadge from '@/components/StatusBadge.vue'

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()
const ordersStore = useOrdersStore()

const order = ref<OrderDetail | null>(null)
const loading = ref(true)
const error = ref('')
const editing = ref(false)
const saving = ref(false)
const showDeleteConfirm = ref(false)
const deleting = ref(false)

interface EditForm {
  order_number: string
  tracking_number: string
  carrier: string
  vendor_name: string
  status: string
  order_date: string
  estimated_delivery: string
}

const editForm = ref<EditForm>({
  order_number: '',
  tracking_number: '',
  carrier: '',
  vendor_name: '',
  status: '',
  order_date: '',
  estimated_delivery: '',
})

const sortedEvents = computed(() => {
  if (!order.value) return []
  return [...order.value.events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  )
})

function startEditing() {
  if (!order.value) return
  editForm.value = {
    order_number: order.value.order_number || '',
    tracking_number: order.value.tracking_number || '',
    carrier: order.value.carrier || '',
    vendor_name: order.value.vendor_name || '',
    status: order.value.status,
    order_date: order.value.order_date?.split('T')[0] || '',
    estimated_delivery: order.value.estimated_delivery?.split('T')[0] || '',
  }
  editing.value = true
}

function cancelEditing() {
  editing.value = false
}

async function saveEdit() {
  if (!order.value) return
  saving.value = true
  try {
    const data: Record<string, string | null> = {}
    if (editForm.value.order_number !== (order.value.order_number || '')) {
      data.order_number = editForm.value.order_number || null
    }
    if (editForm.value.tracking_number !== (order.value.tracking_number || '')) {
      data.tracking_number = editForm.value.tracking_number || null
    }
    if (editForm.value.carrier !== (order.value.carrier || '')) {
      data.carrier = editForm.value.carrier || null
    }
    if (editForm.value.vendor_name !== (order.value.vendor_name || '')) {
      data.vendor_name = editForm.value.vendor_name || null
    }
    if (editForm.value.status !== order.value.status) {
      data.status = editForm.value.status
    }
    if (editForm.value.order_date !== (order.value.order_date?.split('T')[0] || '')) {
      data.order_date = editForm.value.order_date || null
    }
    if (
      editForm.value.estimated_delivery !== (order.value.estimated_delivery?.split('T')[0] || '')
    ) {
      data.estimated_delivery = editForm.value.estimated_delivery || null
    }

    if (Object.keys(data).length > 0) {
      await ordersStore.updateOrder(order.value.id, data)
      // Re-fetch to get updated data with events
      order.value = await ordersStore.fetchOrder(order.value.id)
    }
    editing.value = false
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('orderDetail.saveFailed')
  } finally {
    saving.value = false
  }
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

function formatEventType(type: string): string {
  const key = `status.${type}`
  if (te(key)) return t(key)
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
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
