<template>
  <div
    @click="$router.push({ name: 'order-detail', params: { id: order.id } })"
    class="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
  >
    <div class="flex items-center justify-between mb-1">
      <span class="text-sm font-medium text-gray-900 dark:text-white truncate mr-2">
        {{ order.order_number || order.tracking_number || `#${order.id}` }}
      </span>
      <StatusBadge :status="order.status" />
    </div>
    <div
      v-if="order.tracking_number && order.order_number"
      class="text-xs text-gray-500 dark:text-gray-400 mb-2 truncate"
    >
      {{ order.tracking_number }}
    </div>
    <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
      <span>{{ order.vendor_name || order.vendor_domain || '-' }}</span>
      <span>{{ formatDate(order.order_date || order.created_at) }}</span>
    </div>
    <div
      v-if="order.total_amount"
      class="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right"
    >
      {{ formatAmount(order.total_amount, order.currency) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '@/components/StatusBadge.vue'
import { formatDate, formatAmount } from '@/utils/format'
import type { Order } from '@/stores/orders'

defineProps<{
  order: Order
}>()
</script>
