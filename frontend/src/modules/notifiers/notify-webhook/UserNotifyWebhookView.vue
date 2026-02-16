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
      <!-- Enable/Disable Toggle -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ $t('modules.notify-webhook.title') }}
          </h3>
          <button
            @click="handleToggle"
            :disabled="togglingEnabled"
            class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
            :class="config.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'"
          >
            <span
              class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
              :class="config.enabled ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          {{
            config.enabled ? $t('notifications.enabled') : $t('notifications.disabled')
          }}
        </p>
      </div>

      <!-- Webhook Configuration -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('modules.notify-webhook.webhookUrl') }}
        </h3>

        <div
          v-if="saveSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ $t('modules.notify-webhook.configSaved') }}
        </div>

        <div
          v-if="saveError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ saveError }}
        </div>

        <form @submit.prevent="handleSaveWebhook" class="space-y-4">
          <!-- Webhook URL -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('modules.notify-webhook.webhookUrl')
            }}</label>
            <input
              v-model="webhookForm.url"
              type="url"
              required
              :placeholder="$t('modules.notify-webhook.webhookUrlPlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Auth Header -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('modules.notify-webhook.authHeader')
            }}</label>
            <input
              v-model="webhookForm.auth_header"
              type="password"
              :placeholder="$t('modules.notify-webhook.authHeaderPlaceholder')"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div class="flex items-center gap-3">
            <button
              type="submit"
              :disabled="savingWebhook"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ savingWebhook ? $t('common.saving') : $t('modules.notify-webhook.saveWebhook') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Event Checkboxes -->
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('notifications.events') }}
        </h3>

        <div
          v-if="eventsSaveSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ $t('notifications.configSaved') }}
        </div>

        <div
          v-if="eventsError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ eventsError }}
        </div>

        <form @submit.prevent="handleSaveEvents" class="space-y-3">
          <div class="flex items-start gap-3">
            <input
              id="wh_event_new_order"
              v-model="events.new_order"
              type="checkbox"
              class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
            />
            <label
              for="wh_event_new_order"
              class="text-sm font-medium text-gray-700 dark:text-gray-300"
              >{{ $t('notifications.eventNewOrder') }}</label
            >
          </div>
          <div class="flex items-start gap-3">
            <input
              id="wh_event_tracking_update"
              v-model="events.tracking_update"
              type="checkbox"
              class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
            />
            <label
              for="wh_event_tracking_update"
              class="text-sm font-medium text-gray-700 dark:text-gray-300"
              >{{ $t('notifications.eventTrackingUpdate') }}</label
            >
          </div>
          <div class="flex items-start gap-3">
            <input
              id="wh_event_package_delivered"
              v-model="events.package_delivered"
              type="checkbox"
              class="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
            />
            <label
              for="wh_event_package_delivered"
              class="text-sm font-medium text-gray-700 dark:text-gray-300"
              >{{ $t('notifications.eventPackageDelivered') }}</label
            >
          </div>

          <div class="pt-2">
            <button
              type="submit"
              :disabled="savingEvents"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ savingEvents ? $t('common.saving') : $t('common.save') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Test Section -->
      <div
        v-if="webhookForm.url"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {{ $t('modules.notify-webhook.testWebhook') }}
        </h3>

        <div
          v-if="testSuccess"
          class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ testSuccessMessage }}
        </div>

        <div
          v-if="testError"
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
        >
          {{ testError }}
        </div>

        <button
          @click="handleTest"
          :disabled="testing"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ testing ? $t('common.testing') : $t('modules.notify-webhook.testWebhook') }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { getApiErrorMessage, getApiErrorStatus } from '@/utils/api-error'

const { t } = useI18n()

const loading = ref(true)
const loadError = ref('')

const config = ref({
  enabled: false,
})

const webhookForm = ref({
  url: '',
  auth_header: '',
})

const events = ref({
  new_order: true,
  tracking_update: true,
  package_delivered: true,
})

const togglingEnabled = ref(false)
const savingWebhook = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')

const savingEvents = ref(false)
const eventsError = ref('')
const eventsSaveSuccess = ref(false)

const testing = ref(false)
const testSuccess = ref(false)
const testSuccessMessage = ref('')
const testError = ref('')

async function fetchConfig() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/notifiers/notify-webhook/config')
    config.value.enabled = res.data.enabled ?? false
    webhookForm.value.url = res.data.url || ''
    webhookForm.value.auth_header = ''
    const eventList: string[] = res.data.events || []
    events.value.new_order = eventList.includes('new_order')
    events.value.tracking_update = eventList.includes('tracking_update')
    events.value.package_delivered = eventList.includes('package_delivered')
  } catch (e: unknown) {
    if (getApiErrorStatus(e) !== 404) {
      loadError.value = getApiErrorMessage(e, t('notifications.saveFailed'))
    }
  } finally {
    loading.value = false
  }
}

async function handleToggle() {
  togglingEnabled.value = true
  try {
    const newVal = !config.value.enabled
    await api.put('/notifiers/notify-webhook/config/toggle', { enabled: newVal })
    config.value.enabled = newVal
  } catch (e: unknown) {
    loadError.value = getApiErrorMessage(e, t('notifications.saveFailed'))
  } finally {
    togglingEnabled.value = false
  }
}

async function handleSaveWebhook() {
  saveError.value = ''
  saveSuccess.value = false
  savingWebhook.value = true
  try {
    const payload: Record<string, unknown> = {
      url: webhookForm.value.url,
    }
    if (webhookForm.value.auth_header) {
      payload.auth_header = webhookForm.value.auth_header
    }
    await api.put('/notifiers/notify-webhook/config/webhook', payload)
    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    saveError.value = getApiErrorMessage(e, t('notifications.saveFailed'))
  } finally {
    savingWebhook.value = false
  }
}

async function handleSaveEvents() {
  eventsError.value = ''
  eventsSaveSuccess.value = false
  savingEvents.value = true
  try {
    const eventList = Object.entries(events.value).filter(([_, v]) => v).map(([k]) => k)
    await api.put('/notifiers/notify-webhook/config/events', { events: eventList })
    eventsSaveSuccess.value = true
    setTimeout(() => {
      eventsSaveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    eventsError.value = getApiErrorMessage(e, t('notifications.saveFailed'))
  } finally {
    savingEvents.value = false
  }
}

async function handleTest() {
  testError.value = ''
  testSuccess.value = false
  testSuccessMessage.value = ''
  testing.value = true
  try {
    const res = await api.post('/notifiers/notify-webhook/test', { url: webhookForm.value.url })
    const code = res.data?.response_code || 200
    testSuccessMessage.value = t('modules.notify-webhook.testSuccess', { code })
    testSuccess.value = true
    setTimeout(() => {
      testSuccess.value = false
    }, 5000)
  } catch (e: unknown) {
    testError.value = getApiErrorMessage(e, t('modules.notify-webhook.testFailed'))
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>
