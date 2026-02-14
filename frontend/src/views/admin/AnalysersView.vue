<template>
  <div>
    <!-- Description -->
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">{{ t('analysers.description') }}</p>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ t('common.loading') }}
    </div>

    <!-- Error -->
    <div
      v-if="error"
      class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-6"
    >
      {{ error }}
    </div>

    <!-- Empty State -->
    <div
      v-if="!loading && analysers.length === 0"
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8 text-center"
    >
      <p class="text-gray-500 dark:text-gray-400">{{ t('analysers.empty') }}</p>
    </div>

    <!-- Analyser Cards -->
    <div v-if="!loading && analysers.length > 0" class="space-y-3">
      <div
        v-for="(mod, index) in analysers"
        :key="mod.module_key"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 px-5 py-4"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3 min-w-0">
            <!-- Priority arrows -->
            <div class="flex flex-col gap-0.5">
              <button
                :disabled="index === 0 || reordering"
                @click="moveUp(index)"
                class="p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                :title="t('analysers.moveUp')"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 15l7-7 7 7"
                  />
                </svg>
              </button>
              <button
                :disabled="index === analysers.length - 1 || reordering"
                @click="moveDown(index)"
                class="p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
                :title="t('analysers.moveDown')"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
            </div>

            <!-- Module info -->
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{{ mod.name }}</h3>
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  :class="
                    mod.configured
                      ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400'
                      : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400'
                  "
                >
                  {{ mod.configured ? t('analysers.configured') : t('analysers.notConfigured') }}
                </span>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ mod.description }}</p>
            </div>
          </div>

          <div class="flex items-center gap-3 ml-4">
            <!-- Configure link -->
            <router-link
              v-if="configPath(mod.module_key)"
              :to="configPath(mod.module_key)!"
              class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              {{ t('analysers.configure') }}
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { getModulesByType } from '@/core/moduleRegistry'

const { t } = useI18n()

interface AnalyserModule {
  module_key: string
  enabled: boolean
  configured: boolean
  priority: number
  name: string | null
  type: string | null
  description: string | null
}

const analysers = ref<AnalyserModule[]>([])
const loading = ref(false)
const error = ref('')
const reordering = ref(false)

function configPath(moduleKey: string): string | null {
  const manifests = getModulesByType('analyser')
  const manifest = manifests.find((m) => m.key === moduleKey)
  if (manifest && manifest.adminRoutes.length > 0) {
    return `/admin/settings/${manifest.adminRoutes[0].path}`
  }
  return null
}

async function fetchAnalysers() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<AnalyserModule[]>('/modules')
    analysers.value = res.data
      .filter((m) => m.type === 'analyser')
      .sort((a, b) => a.priority - b.priority)
  } catch {
    error.value = 'Failed to load analyser modules.'
  } finally {
    loading.value = false
  }
}

async function saveOrder() {
  reordering.value = true
  error.value = ''
  try {
    const keys = analysers.value.map((m) => m.module_key)
    await api.patch('/modules/priority', { module_keys: keys })
  } catch {
    error.value = 'Failed to save priority order.'
  } finally {
    reordering.value = false
  }
}

function moveUp(index: number) {
  if (index <= 0) return
  const arr = [...analysers.value]
  ;[arr[index - 1], arr[index]] = [arr[index], arr[index - 1]]
  analysers.value = arr
  saveOrder()
}

function moveDown(index: number) {
  if (index >= analysers.value.length - 1) return
  const arr = [...analysers.value]
  ;[arr[index], arr[index + 1]] = [arr[index + 1], arr[index]]
  analysers.value = arr
  saveOrder()
}

onMounted(() => {
  fetchAnalysers()
})
</script>
