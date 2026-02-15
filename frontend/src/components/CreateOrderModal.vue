<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="fixed inset-0 bg-black/50" @click="$emit('close')"></div>
    <div
      class="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto"
    >
      <!-- Header -->
      <div
        class="sticky top-0 bg-white dark:bg-gray-900 px-6 py-4 border-b border-gray-200 dark:border-gray-700 z-10"
      >
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
          {{ $t('orders.newOrder') }}
        </h2>
      </div>

      <form @submit.prevent="submit" class="p-6 space-y-6">
        <!-- Error -->
        <div
          v-if="error"
          class="bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/30 dark:border-red-800 dark:text-red-400 px-4 py-3 rounded-md text-sm"
        >
          {{ error }}
        </div>

        <!-- Section 1: Order Info -->
        <div>
          <h3
            class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3"
          >
            {{ $t('orders.sectionOrderInfo') }}
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.vendorName') }} *
              </label>
              <input
                v-model="form.vendor_name"
                type="text"
                required
                :placeholder="$t('orders.vendorNamePlaceholder')"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.vendorDomain') }}
              </label>
              <input
                v-model="form.vendor_domain"
                type="text"
                :placeholder="$t('orders.vendorDomainPlaceholder')"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.orderNumber') }}
              </label>
              <input
                v-model="form.order_number"
                type="text"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.orderDate') }}
              </label>
              <input
                v-model="form.order_date"
                type="date"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orderDetail.status') }}
              </label>
              <select
                v-model="form.status"
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
          </div>
        </div>

        <!-- Section 2: Shipping -->
        <div>
          <h3
            class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3"
          >
            {{ $t('orders.sectionShipping') }}
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.trackingNumber') }}
              </label>
              <input
                v-model="form.tracking_number"
                type="text"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.carrierField') }}
              </label>
              <input
                v-model="form.carrier"
                type="text"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.estimatedDelivery') }}
              </label>
              <input
                v-model="form.estimated_delivery"
                type="date"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- Section 3: Cost -->
        <div>
          <h3
            class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3"
          >
            {{ $t('orders.sectionCost') }}
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.totalAmount') }}
              </label>
              <input
                v-model.number="form.total_amount"
                type="number"
                step="0.01"
                min="0"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                {{ $t('orders.currency') }}
              </label>
              <input
                v-model="form.currency"
                type="text"
                placeholder="EUR"
                class="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        <!-- Section 4: Items -->
        <div>
          <h3
            class="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-3"
          >
            {{ $t('orders.sectionItems') }}
          </h3>

          <div v-if="form.items.length > 0" class="space-y-2 mb-3">
            <div
              v-for="(item, idx) in form.items"
              :key="idx"
              class="flex items-center gap-2"
            >
              <input
                v-model="item.name"
                type="text"
                required
                :placeholder="$t('orders.itemName')"
                class="flex-1 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                v-model.number="item.quantity"
                type="number"
                min="1"
                :placeholder="$t('orders.itemQuantity')"
                class="w-16 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                v-model.number="item.price"
                type="number"
                step="0.01"
                min="0"
                :placeholder="$t('orders.itemPrice')"
                class="w-24 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                @click="removeItem(idx)"
                class="p-1.5 text-gray-400 hover:text-red-500 dark:hover:text-red-400"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>

          <button
            type="button"
            @click="addItem"
            class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
          >
            + {{ $t('orders.addItem') }}
          </button>
        </div>

        <!-- Footer -->
        <div
          class="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700"
        >
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:text-gray-300 dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            type="submit"
            :disabled="submitting"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {{ submitting ? $t('orders.creating') : $t('orders.createOrder') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdersStore } from '@/stores/orders'

const emit = defineEmits<{
  close: []
  created: [id: number]
}>()

const { t } = useI18n()
const ordersStore = useOrdersStore()

const submitting = ref(false)
const error = ref('')

interface FormItem {
  name: string
  quantity: number
  price: number | null
}

const form = ref({
  vendor_name: '',
  vendor_domain: '',
  order_number: '',
  order_date: new Date().toISOString().split('T')[0],
  status: 'ordered',
  tracking_number: '',
  carrier: '',
  estimated_delivery: '',
  total_amount: null as number | null,
  currency: 'EUR',
  items: [] as FormItem[],
})

function addItem() {
  form.value.items.push({ name: '', quantity: 1, price: null })
}

function removeItem(idx: number) {
  form.value.items.splice(idx, 1)
}

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const data: Record<string, unknown> = {
      vendor_name: form.value.vendor_name,
      status: form.value.status,
    }
    if (form.value.vendor_domain) data.vendor_domain = form.value.vendor_domain
    if (form.value.order_number) data.order_number = form.value.order_number
    if (form.value.order_date) data.order_date = form.value.order_date
    if (form.value.tracking_number) data.tracking_number = form.value.tracking_number
    if (form.value.carrier) data.carrier = form.value.carrier
    if (form.value.estimated_delivery) data.estimated_delivery = form.value.estimated_delivery
    if (form.value.total_amount !== null) data.total_amount = form.value.total_amount
    if (form.value.currency) data.currency = form.value.currency
    if (form.value.items.length > 0) data.items = form.value.items

    const order = await ordersStore.createOrder(data as any)
    emit('created', order.id)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('orders.createFailed')
  } finally {
    submitting.value = false
  }
}
</script>
