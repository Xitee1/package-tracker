<template>
  <div
    class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
  >
    <div
      v-if="loadError"
      class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
    >
      {{ loadError }}
    </div>

    <div v-if="loading" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>

    <form v-else @submit.prevent="handleSave" class="space-y-5">
      <div
        v-if="saveSuccess"
        class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm"
      >
        {{ $t('queue.configSaved') }}
      </div>

      <div
        v-if="saveError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
      >
        {{ saveError }}
      </div>

      <!-- Max Age Days -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('queue.maxAgeDays')
        }}</label>
        <input
          v-model.number="form.max_age_days"
          type="number"
          required
          min="1"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {{ $t('queue.maxAgeDaysHint') }}
        </p>
      </div>

      <!-- Max Per User -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('queue.maxPerUser')
        }}</label>
        <input
          v-model.number="form.max_per_user"
          type="number"
          required
          min="1"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {{ $t('queue.maxPerUserHint') }}
        </p>
      </div>

      <!-- Save Button -->
      <div class="pt-2">
        <button
          type="submit"
          :disabled="saving"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? $t('common.saving') : $t('queue.saveSettings') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'

const { t } = useI18n()

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)

const form = ref({
  max_age_days: 30,
  max_per_user: 1000,
})

async function fetchSettings() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/settings/queue/')
    form.value.max_age_days = res.data.max_age_days
    form.value.max_per_user = res.data.max_per_user
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    loadError.value = err.response?.data?.detail || t('queue.loadFailed')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    await api.patch('/settings/queue/', form.value)
    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    saveError.value = err.response?.data?.detail || t('queue.saveFailed')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>
