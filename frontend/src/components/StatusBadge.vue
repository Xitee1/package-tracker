<template>
  <span
    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    :class="badgeClass"
  >
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
}>()

const statusConfig: Record<string, { class: string; label: string }> = {
  ordered: {
    class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    label: 'Ordered',
  },
  shipment_preparing: {
    class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    label: 'Preparing',
  },
  shipped: {
    class: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
    label: 'Shipped',
  },
  in_transit: {
    class: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    label: 'In Transit',
  },
  out_for_delivery: {
    class: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
    label: 'Out for Delivery',
  },
  delivered: {
    class: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    label: 'Delivered',
  },
}

const badgeClass = computed(() => {
  return (
    statusConfig[props.status]?.class ||
    'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  )
})

const label = computed(() => {
  return (
    statusConfig[props.status]?.label ||
    props.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  )
})
</script>
