<template>
  <div class="space-y-6">
    <!-- Load Error -->
    <div
      v-if="loadError"
      class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
    >
      {{ loadError }}
    </div>

    <div v-if="loading" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>

    <template v-else>
      <!-- Phase 1: Connection Details -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('globalMail.connectionTitle') }}
        </h3>

        <div
          v-if="connectionSaveSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ $t('globalMail.configSaved') }}
        </div>

        <div
          v-if="connectionSaveError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ connectionSaveError }}
        </div>

        <form @submit.prevent="handleSaveConnection" class="space-y-5">
          <!-- IMAP Host -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('globalMail.imapHost')
            }}</label>
            <input
              v-model="connectionForm.imap_host"
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
              v-model.number="connectionForm.imap_port"
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
              v-model="connectionForm.imap_user"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {{ $t('globalMail.password') }}
              <span v-if="configExists" class="text-xs text-gray-400 dark:text-gray-500 ml-1">{{
                $t('globalMail.passwordKeepCurrent')
              }}</span>
            </label>
            <input
              v-model="connectionForm.imap_password"
              type="password"
              :required="!configExists"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Use SSL -->
          <div class="flex items-start gap-3">
            <input
              id="use_ssl"
              v-model="connectionForm.use_ssl"
              type="checkbox"
              class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
            />
            <label for="use_ssl" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
              $t('globalMail.useSsl')
            }}</label>
          </div>

          <!-- Save Connection Button -->
          <div class="pt-2">
            <button
              type="submit"
              :disabled="savingConnection"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ savingConnection ? $t('common.saving') : $t('globalMail.saveConnection') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Phase 2: Mail Settings (only when config exists) -->
      <div
        v-if="configExists"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('globalMail.settingsTitle') }}
        </h3>

        <div
          v-if="settingsSaveSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ $t('globalMail.configSaved') }}
        </div>

        <div
          v-if="settingsSaveError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ settingsSaveError }}
        </div>

        <form @submit.prevent="handleSaveSettings" class="space-y-5">
          <!-- Watched Folder Dropdown -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('globalMail.watchedFolder')
            }}</label>

            <div v-if="loadingFolders" class="text-sm text-gray-500 dark:text-gray-400 py-2">
              {{ $t('globalMail.loadingFolders') }}
            </div>

            <div v-else-if="folderLoadError" class="space-y-2">
              <div
                class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
              >
                {{ $t('globalMail.folderLoadError') }}
              </div>
              <button
                type="button"
                @click="fetchFolders"
                class="px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 border border-blue-300 dark:border-blue-600 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/30"
              >
                {{ $t('globalMail.retry') }}
              </button>
            </div>

            <select
              v-else
              v-model="settingsForm.watched_folder_path"
              required
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option v-for="folder in folders" :key="folder" :value="folder">
                {{ folder }}
              </option>
            </select>
          </div>

          <!-- IDLE/Polling info -->
          <div v-if="idleSupported !== null" class="text-sm text-gray-500 dark:text-gray-400">
            <template v-if="idleSupported">
              {{ $t('globalMail.idleHint') }}
            </template>
            <template v-else>
              {{ $t('globalMail.pollingHint') }}
            </template>
          </div>

          <!-- Polling Interval (only when IDLE not supported) -->
          <div v-if="idleSupported === false">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('globalMail.pollingInterval')
            }}</label>
            <input
              v-model.number="settingsForm.polling_interval_sec"
              type="number"
              required
              min="10"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Save Settings Button -->
          <div class="pt-2">
            <button
              type="submit"
              :disabled="savingSettings || loadingFolders"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ savingSettings ? $t('common.saving') : $t('globalMail.saveSettings') }}
            </button>
          </div>
        </form>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'

const { t } = useI18n()

const loading = ref(true)
const loadError = ref('')
const configExists = ref(false)

// Phase 1: Connection
const connectionForm = ref({
  imap_host: '',
  imap_port: 993,
  imap_user: '',
  imap_password: '',
  use_ssl: true,
})
const savingConnection = ref(false)
const connectionSaveError = ref('')
const connectionSaveSuccess = ref(false)

// Phase 2: Settings
const settingsForm = ref({
  watched_folder_path: 'INBOX',
  polling_interval_sec: 300,
})
const savingSettings = ref(false)
const settingsSaveError = ref('')
const settingsSaveSuccess = ref(false)

// Folders
const folders = ref<string[]>([])
const loadingFolders = ref(false)
const folderLoadError = ref(false)
const idleSupported = ref<boolean | null>(null)

async function fetchSettings() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/modules/providers/email-global/config')
    if (res.data) {
      configExists.value = true
      connectionForm.value.imap_host = res.data.imap_host || ''
      connectionForm.value.imap_port = res.data.imap_port ?? 993
      connectionForm.value.imap_user = res.data.imap_user || ''
      connectionForm.value.imap_password = ''
      connectionForm.value.use_ssl = res.data.use_ssl ?? true
      settingsForm.value.watched_folder_path = res.data.watched_folder_path || 'INBOX'
      settingsForm.value.polling_interval_sec = res.data.polling_interval_sec ?? 300
      idleSupported.value = res.data.idle_supported ?? null
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    loadError.value = err.response?.data?.detail || t('globalMail.saveFailed')
  } finally {
    loading.value = false
  }
}

async function fetchFolders() {
  loadingFolders.value = true
  folderLoadError.value = false
  try {
    const res = await api.get('/modules/providers/email-global/folders')
    folders.value = res.data.folders
    idleSupported.value = res.data.idle_supported
  } catch {
    folderLoadError.value = true
  } finally {
    loadingFolders.value = false
  }
}

async function handleSaveConnection() {
  connectionSaveError.value = ''
  connectionSaveSuccess.value = false
  savingConnection.value = true
  try {
    const payload: Record<string, unknown> = {
      ...connectionForm.value,
      watched_folder_path: settingsForm.value.watched_folder_path,
      polling_interval_sec: settingsForm.value.polling_interval_sec,
    }
    if (!payload.imap_password) {
      delete payload.imap_password
    }
    await api.put('/modules/providers/email-global/config', payload)
    connectionSaveSuccess.value = true
    configExists.value = true
    setTimeout(() => {
      connectionSaveSuccess.value = false
    }, 3000)
    // Fetch folders after saving connection
    await fetchFolders()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    connectionSaveError.value = err.response?.data?.detail || t('globalMail.saveFailed')
  } finally {
    savingConnection.value = false
  }
}

async function handleSaveSettings() {
  settingsSaveError.value = ''
  settingsSaveSuccess.value = false
  savingSettings.value = true
  try {
    const payload: Record<string, unknown> = {
      ...connectionForm.value,
      watched_folder_path: settingsForm.value.watched_folder_path,
      polling_interval_sec: settingsForm.value.polling_interval_sec,
      use_polling: idleSupported.value === false,
    }
    if (!payload.imap_password) {
      delete payload.imap_password
    }
    await api.put('/modules/providers/email-global/config', payload)
    settingsSaveSuccess.value = true
    setTimeout(() => {
      settingsSaveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    settingsSaveError.value = err.response?.data?.detail || t('globalMail.saveFailed')
  } finally {
    savingSettings.value = false
  }
}

onMounted(async () => {
  await fetchSettings()
  if (configExists.value) {
    await fetchFolders()
  }
})
</script>
