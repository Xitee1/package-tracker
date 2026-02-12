<template>
  <div class="p-6 max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">{{ $t('profile.title') }}</h1>

    <!-- Language -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
        {{ $t('profile.language') }}
      </h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {{ $t('profile.languageDescription') }}
      </p>
      <select
        :value="locale"
        @change="setLocale(($event.target as HTMLSelectElement).value)"
        class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        <option value="en">English</option>
        <option value="de">Deutsch</option>
      </select>
    </div>

    <!-- Theme -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
        {{ $t('profile.theme') }}
      </h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {{ $t('profile.themeDescription') }}
      </p>
      <ThemeToggle />
    </div>

    <!-- Change Password -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {{ $t('profile.changePassword') }}
      </h2>

      <div
        v-if="success"
        class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ success }}
      </div>

      <div
        v-if="error"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ error }}
      </div>

      <form @submit.prevent="handleChangePassword" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
            $t('profile.currentPassword')
          }}</label>
          <input
            v-model="form.currentPassword"
            type="password"
            required
            autocomplete="current-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="$t('profile.currentPasswordPlaceholder')"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
            $t('profile.newPassword')
          }}</label>
          <input
            v-model="form.newPassword"
            type="password"
            required
            autocomplete="new-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="$t('profile.newPasswordPlaceholder')"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
            $t('profile.confirmNewPassword')
          }}</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            required
            autocomplete="new-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="$t('profile.confirmPasswordPlaceholder')"
          />
        </div>

        <div class="pt-2">
          <button
            type="submit"
            :disabled="saving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? $t('profile.updating') : $t('profile.updatePassword') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import ThemeToggle from '@/components/ThemeToggle.vue'

const { t, locale } = useI18n()
const auth = useAuthStore()

const saving = ref(false)
const error = ref('')
const success = ref('')

const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

function setLocale(newLocale: string) {
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
  document.documentElement.lang = newLocale
}

async function handleChangePassword() {
  error.value = ''
  success.value = ''

  if (form.value.newPassword !== form.value.confirmPassword) {
    error.value = t('profile.passwordsNoMatch')
    return
  }

  if (form.value.newPassword.length < 6) {
    error.value = t('profile.passwordMinLength')
    return
  }

  saving.value = true
  try {
    await api.patch(`/users/${auth.user!.id}`, {
      password: form.value.newPassword,
      current_password: form.value.currentPassword,
    })
    success.value = t('profile.passwordUpdated')
    form.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
    setTimeout(() => {
      success.value = ''
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('profile.updateFailed')
  } finally {
    saving.value = false
  }
}
</script>
