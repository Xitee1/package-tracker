<template>
  <div class="mb-6">
    <div
      class="flex items-center justify-between bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-5 py-4"
    >
      <div>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{{ name }}</h2>
        <p v-if="description" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          {{ description }}
        </p>
      </div>
      <button
        @click="handleToggle"
        :disabled="toggling"
        class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 disabled:opacity-50"
        :class="enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'"
      >
        <span
          class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
          :class="enabled ? 'translate-x-5' : 'translate-x-0'"
        />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'
import { useModulesStore } from '@/stores/modules'

const props = defineProps<{
  moduleKey: string
  name: string
  description?: string
  enabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:enabled', value: boolean): void
}>()

const modulesStore = useModulesStore()
const toggling = ref(false)

async function handleToggle() {
  toggling.value = true
  try {
    const newValue = !props.enabled
    await api.put(`/modules/${props.moduleKey}`, { enabled: newValue })
    emit('update:enabled', newValue)
    await modulesStore.fetchModules()
  } finally {
    toggling.value = false
  }
}
</script>
