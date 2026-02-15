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
      <!-- SMTP Configuration -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('smtp.title') }}
        </h3>

        <div
          v-if="saveSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ $t('smtp.configSaved') }}
        </div>

        <div
          v-if="saveError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ saveError }}
        </div>

        <form @submit.prevent="handleSave" class="space-y-5">
          <!-- SMTP Host -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('smtp.host')
            }}</label>
            <input
              v-model="form.host"
              type="text"
              required
              :placeholder="$t('smtp.hostPlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Port -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('smtp.port')
            }}</label>
            <input
              v-model.number="form.port"
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
              $t('smtp.username')
            }}</label>
            <input
              v-model="form.username"
              type="text"
              :placeholder="$t('smtp.usernamePlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {{ $t('smtp.password') }}
              <span v-if="configExists" class="text-xs text-gray-400 dark:text-gray-500 ml-1">{{
                $t('smtp.passwordKeepCurrent')
              }}</span>
            </label>
            <input
              v-model="form.password"
              type="password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Use TLS -->
          <div class="flex items-start gap-3">
            <input
              id="use_tls"
              v-model="form.use_tls"
              type="checkbox"
              class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
            />
            <label for="use_tls" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
              $t('smtp.useTls')
            }}</label>
          </div>

          <!-- Sender Address -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('smtp.senderAddress')
            }}</label>
            <input
              v-model="form.sender_address"
              type="email"
              required
              :placeholder="$t('smtp.senderAddressPlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Sender Name -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('smtp.senderName')
            }}</label>
            <input
              v-model="form.sender_name"
              type="text"
              :placeholder="$t('smtp.senderNamePlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Save Button -->
          <div class="pt-2">
            <button
              type="submit"
              :disabled="saving"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ saving ? $t('common.saving') : $t('smtp.saveConfig') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Test Email Section -->
      <div
        v-if="configExists"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('smtp.testConnection') }}
        </h3>

        <div
          v-if="testSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ $t('smtp.testSuccess') }}
        </div>

        <div
          v-if="testError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ testError }}
        </div>

        <form @submit.prevent="handleTest" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('smtp.testRecipient')
            }}</label>
            <input
              v-model="testRecipient"
              type="email"
              required
              :placeholder="$t('smtp.testRecipientPlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            :disabled="testing"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ testing ? $t('common.testing') : $t('smtp.testConnection') }}
          </button>
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

const form = ref({
  host: '',
  port: 587,
  username: '',
  password: '',
  use_tls: true,
  sender_address: '',
  sender_name: '',
})

const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)

const testRecipient = ref('')
const testing = ref(false)
const testError = ref('')
const testSuccess = ref(false)

async function fetchConfig() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/admin/smtp')
    if (res.data && res.data.host) {
      configExists.value = true
      form.value.host = res.data.host || ''
      form.value.port = res.data.port ?? 587
      form.value.username = res.data.username || ''
      form.value.password = ''
      form.value.use_tls = res.data.use_tls ?? true
      form.value.sender_address = res.data.sender_address || ''
      form.value.sender_name = res.data.sender_name || ''
    }
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: string } } }
    if (err.response?.status !== 404) {
      loadError.value = err.response?.data?.detail || t('smtp.loadFailed')
    }
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
    if (!payload.password) {
      delete payload.password
    }
    await api.put('/admin/smtp', payload)
    saveSuccess.value = true
    configExists.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    saveError.value = err.response?.data?.detail || t('smtp.saveFailed')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testError.value = ''
  testSuccess.value = false
  testing.value = true
  try {
    await api.post('/admin/smtp/test', { recipient: testRecipient.value })
    testSuccess.value = true
    setTimeout(() => {
      testSuccess.value = false
    }, 5000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    testError.value = err.response?.data?.detail || t('smtp.testFailed')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>
