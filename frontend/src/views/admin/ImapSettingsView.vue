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
        {{ $t('imap.configSaved') }}
      </div>

      <div
        v-if="saveError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
      >
        {{ saveError }}
      </div>

      <!-- Max Email Age -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('imap.maxEmailAgeDays')
        }}</label>
        <input
          v-model.number="form.max_email_age_days"
          type="number"
          required
          min="1"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {{ $t('imap.maxEmailAgeDaysHint') }}
        </p>
      </div>

      <!-- Processing Delay -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('imap.processingDelaySec')
        }}</label>
        <input
          v-model.number="form.processing_delay_sec"
          type="number"
          required
          min="0"
          step="0.5"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {{ $t('imap.processingDelaySecHint') }}
        </p>
      </div>

      <!-- Check UIDVALIDITY -->
      <div class="flex items-start gap-3">
        <input
          id="check_uidvalidity"
          v-model="form.check_uidvalidity"
          type="checkbox"
          class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
        />
        <div>
          <label
            for="check_uidvalidity"
            class="text-sm font-medium text-gray-700 dark:text-gray-300"
            >{{ $t('imap.checkUidvalidity') }}</label
          >
          <p class="text-xs text-gray-500 dark:text-gray-400">
            {{ $t('imap.checkUidvalidityHint') }}
          </p>
        </div>
      </div>

      <!-- Save Button -->
      <div class="pt-2">
        <button
          type="submit"
          :disabled="saving"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? $t('common.saving') : $t('imap.saveSettings') }}
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
  max_email_age_days: 7,
  processing_delay_sec: 2.0,
  check_uidvalidity: true,
})

async function fetchSettings() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/settings/imap')
    form.value.max_email_age_days = res.data.max_email_age_days
    form.value.processing_delay_sec = res.data.processing_delay_sec
    form.value.check_uidvalidity = res.data.check_uidvalidity
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    loadError.value = err.response?.data?.detail || t('imap.loadFailed')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    await api.put('/settings/imap', form.value)
    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    saveError.value = err.response?.data?.detail || t('imap.saveFailed')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>
