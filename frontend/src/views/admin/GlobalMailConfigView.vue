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
        {{ $t('globalMail.configSaved') }}
      </div>

      <div
        v-if="saveError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
      >
        {{ saveError }}
      </div>

      <!-- IMAP Host -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('globalMail.imapHost')
        }}</label>
        <input
          v-model="form.imap_host"
          type="text"
          required
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- IMAP Port -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('globalMail.imapPort')
        }}</label>
        <input
          v-model.number="form.imap_port"
          type="number"
          required
          min="1"
          max="65535"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Username -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('globalMail.username')
        }}</label>
        <input
          v-model="form.imap_user"
          type="text"
          required
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Password -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {{ $t('globalMail.password') }}
          <span class="text-xs text-gray-400 dark:text-gray-500 ml-1">{{
            $t('globalMail.passwordKeepCurrent')
          }}</span>
        </label>
        <input
          v-model="form.imap_password"
          type="password"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Use SSL -->
      <div class="flex items-start gap-3">
        <input
          id="use_ssl"
          v-model="form.use_ssl"
          type="checkbox"
          class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
        />
        <label for="use_ssl" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
          $t('globalMail.useSsl')
        }}</label>
      </div>

      <!-- Polling Interval -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('globalMail.pollingInterval')
        }}</label>
        <input
          v-model.number="form.polling_interval_sec"
          type="number"
          required
          min="10"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Use Polling -->
      <div class="flex items-start gap-3">
        <input
          id="use_polling"
          v-model="form.use_polling"
          type="checkbox"
          class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
        />
        <label for="use_polling" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
          $t('globalMail.usePolling')
        }}</label>
      </div>

      <!-- Watched Folder -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
          $t('globalMail.watchedFolder')
        }}</label>
        <input
          v-model="form.watched_folder_path"
          type="text"
          required
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <!-- Is Active -->
      <div class="flex items-start gap-3">
        <input
          id="is_active"
          v-model="form.is_active"
          type="checkbox"
          class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
        />
        <label for="is_active" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
          $t('globalMail.isActive')
        }}</label>
      </div>

      <!-- Save Button -->
      <div class="pt-2">
        <button
          type="submit"
          :disabled="saving"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ saving ? $t('common.saving') : $t('globalMail.saveSettings') }}
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
  imap_host: '',
  imap_port: 993,
  imap_user: '',
  imap_password: '',
  use_ssl: true,
  polling_interval_sec: 300,
  use_polling: false,
  watched_folder_path: 'INBOX',
  is_active: false,
})

async function fetchSettings() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/settings/global-mail')
    if (res.data) {
      form.value.imap_host = res.data.imap_host || ''
      form.value.imap_port = res.data.imap_port ?? 993
      form.value.imap_user = res.data.imap_user || ''
      form.value.imap_password = ''
      form.value.use_ssl = res.data.use_ssl ?? true
      form.value.polling_interval_sec = res.data.polling_interval_sec ?? 300
      form.value.use_polling = res.data.use_polling ?? false
      form.value.watched_folder_path = res.data.watched_folder_path || 'INBOX'
      form.value.is_active = res.data.is_active ?? false
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    loadError.value = err.response?.data?.detail || t('globalMail.saveFailed')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form.value }
    if (!payload.imap_password) {
      delete payload.imap_password
    }
    await api.put('/settings/global-mail', payload)
    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    saveError.value = err.response?.data?.detail || t('globalMail.saveFailed')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>
