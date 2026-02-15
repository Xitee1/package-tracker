<template>
  <div class="flex items-center justify-center min-h-[60vh]">
    <div class="text-center max-w-md">
      <div v-if="loading" class="text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</div>
      <div v-else-if="success" class="text-green-600 dark:text-green-400">
        <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p class="text-lg font-medium">{{ $t('modules.notify-email.verifySuccess') }}</p>
      </div>
      <div v-else class="text-red-600 dark:text-red-400">
        <p class="text-lg font-medium">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'

const route = useRoute()
const { t } = useI18n()
const loading = ref(true)
const success = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    await api.post(`/notifiers/notify-email/verify/${route.params.token}`)
    success.value = true
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value =
      err.response?.data?.detail === 'Verification link expired'
        ? t('modules.notify-email.verifyExpired')
        : t('modules.notify-email.verifyFailed')
  } finally {
    loading.value = false
  }
})
</script>
