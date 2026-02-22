<template>
  <div>
    <!-- Info box showing the global inbox address -->
    <div
      v-if="globalInfo.configured"
      class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6"
    >
      <p class="text-sm text-blue-800 dark:text-blue-300">
        {{ $t('forwarding.infoText') }}
        <span class="font-mono font-semibold">{{ globalInfo.email_address }}</span>
      </p>
    </div>

    <!-- Add form -->
    <div class="mb-6">
      <form @submit.prevent="handleAdd" class="flex gap-3 items-end">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ $t('forwarding.emailAddress') }}
          </label>
          <input
            v-model="newEmail"
            type="email"
            required
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="$t('forwarding.emailPlaceholder')"
          />
        </div>
        <button
          type="submit"
          :disabled="adding"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {{ adding ? $t('common.saving') : $t('forwarding.addAddress') }}
        </button>
      </form>
      <p v-if="error" class="mt-2 text-sm text-red-600 dark:text-red-400">{{ error }}</p>
    </div>

    <!-- Address list -->
    <div v-if="store.loading" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>
    <div
      v-else-if="store.addresses.length === 0"
      class="text-center py-8 text-gray-500 dark:text-gray-400"
    >
      {{ $t('forwarding.noAddresses') }}
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="addr in store.addresses"
        :key="addr.id"
        class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-3"
      >
        <span class="text-sm text-gray-900 dark:text-white">{{ addr.email_address }}</span>
        <button
          @click="handleDelete(addr.id)"
          :disabled="deletingId === addr.id"
          class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
        >
          {{ deletingId === addr.id ? $t('common.deleting') : $t('common.delete') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { getApiErrorMessage } from '@/utils/api-error'
import { useSenderAddressesStore } from './store'

const { t } = useI18n()
const store = useSenderAddressesStore()

const newEmail = ref('')
const adding = ref(false)
const error = ref('')
const deletingId = ref<number | null>(null)
const globalInfo = reactive({ configured: false, email_address: '' })

async function fetchGlobalInfo() {
  try {
    const res = await api.get('/providers/email-global/info')
    globalInfo.configured = res.data.configured
    globalInfo.email_address = res.data.email_address || ''
  } catch {
    // Not available
  }
}

async function handleAdd() {
  error.value = ''
  adding.value = true
  try {
    await store.addAddress(newEmail.value)
    newEmail.value = ''
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('forwarding.addFailed'))
  } finally {
    adding.value = false
  }
}

async function handleDelete(id: number) {
  deletingId.value = id
  try {
    await store.removeAddress(id)
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('forwarding.deleteFailed'))
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  store.fetchAddresses()
  fetchGlobalInfo()
})
</script>
