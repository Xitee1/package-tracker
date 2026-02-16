<template>
  <!-- Loading state while setup status is unknown -->
  <div
    v-if="auth.setupCompleted === null"
    class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950"
  >
    <p class="text-gray-500 dark:text-gray-400">{{ $t('common.loading') }}</p>
  </div>

  <!-- Setup form -->
  <div
    v-else-if="auth.setupCompleted === false"
    class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950"
  >
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-8">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('app.title') }}</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">{{ $t('login.createAdmin') }}</p>
        </div>

        <form @submit.prevent="handleSetup" class="space-y-5">
          <div
            v-if="error"
            class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
          >
            {{ error }}
          </div>

          <div>
            <label
              for="username"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >{{ $t('login.username') }}</label
            >
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('login.chooseUsername')"
            />
          </div>

          <div>
            <label
              for="password"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >{{ $t('login.password') }}</label
            >
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('login.choosePassword')"
            />
          </div>

          <div>
            <label
              for="confirmPassword"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >{{ $t('login.confirmPassword') }}</label
            >
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('login.confirmYourPassword')"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">{{ $t('login.creatingAccount') }}</span>
            <span v-else>{{ $t('login.createAdmin') }}</span>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- Login form -->
  <div v-else class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-8">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('app.title') }}</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">{{ $t('login.signIn') }}</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div
            v-if="error"
            class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
          >
            {{ error }}
          </div>

          <div>
            <label
              for="username"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >{{ $t('login.username') }}</label
            >
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('login.enterUsername')"
            />
          </div>

          <div>
            <label
              for="password"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >{{ $t('login.password') }}</label
            >
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('login.enterPassword')"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">{{ $t('login.signingIn') }}</span>
            <span v-else>{{ $t('login.signInButton') }}</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { getApiErrorMessage } from '@/utils/api-error'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleSetup() {
  error.value = ''

  if (password.value !== confirmPassword.value) {
    error.value = t('login.passwordsNoMatch')
    return
  }

  if (password.value.length < 6) {
    error.value = t('login.passwordMinLength')
    return
  }

  loading.value = true
  try {
    await auth.setup(username.value, password.value)
    auth.setupCompleted = true
    router.push('/dashboard')
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('login.setupFailed'))
  } finally {
    loading.value = false
  }
}

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('login.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>
