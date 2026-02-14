<template>
  <div>
    <div v-if="loading" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>
    <div v-else class="space-y-4">
      <div
        v-for="mod in modulesStore.modules"
        :key="mod.module_key"
        class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-4"
      >
        <div>
          <h3 class="text-sm font-medium text-gray-900 dark:text-white">
            {{ $t(`modules.${mod.module_key}.title`) }}
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {{ $t(`modules.${mod.module_key}.description`) }}
          </p>
        </div>
        <button
          @click="handleToggle(mod.module_key, !mod.enabled)"
          :disabled="toggling === mod.module_key"
          class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          :class="mod.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
            :class="mod.enabled ? 'translate-x-5' : 'translate-x-0'"
          />
        </button>
      </div>
    </div>
    <p v-if="error" class="mt-4 text-sm text-red-600 dark:text-red-400">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { useModulesStore } from '@/stores/modules'

const { t } = useI18n()
const modulesStore = useModulesStore()
const loading = ref(false)
const toggling = ref<string | null>(null)
const error = ref('')

async function handleToggle(key: string, enabled: boolean) {
  toggling.value = key
  error.value = ''
  try {
    await api.put(`/modules/${key}`, { enabled })
    await modulesStore.fetchModules()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('modules.toggleFailed')
  } finally {
    toggling.value = null
  }
}

onMounted(async () => {
  loading.value = true
  await modulesStore.fetchModules()
  loading.value = false
})
</script>
