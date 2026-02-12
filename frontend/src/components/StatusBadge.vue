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
import { useI18n } from 'vue-i18n'

const { t, te } = useI18n()

const props = defineProps<{
  status: string
}>()

const statusConfig: Record<string, string> = {
  ordered: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  shipment_preparing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  shipped: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
  in_transit: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  out_for_delivery: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  delivered: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
}

const badgeClass = computed(() => {
  return statusConfig[props.status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
})

const label = computed(() => {
  const key = `status.${props.status}`
  if (te(key)) return t(key)
  return props.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
})
</script>
