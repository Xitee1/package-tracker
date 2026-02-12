<template>
  <!-- Loading state while setup status is unknown -->
  <div
    v-if="auth.setupCompleted === null"
    class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950"
  >
    <p class="text-gray-500 dark:text-gray-400">Loading...</p>
  </div>

  <!-- Setup form -->
  <div
    v-else-if="auth.setupCompleted === false"
    class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950"
  >
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-8">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Package Tracker</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Create Admin Account</p>
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
              >Username</label
            >
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Choose a username"
            />
          </div>

          <div>
            <label
              for="password"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >Password</label
            >
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Choose a password"
            />
          </div>

          <div>
            <label
              for="confirmPassword"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >Confirm Password</label
            >
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Confirm your password"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">Creating account...</span>
            <span v-else>Create Admin Account</span>
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
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Package Tracker</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Sign in to your account</p>
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
              >Username</label
            >
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label
              for="password"
              class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >Password</label
            >
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">Signing in...</span>
            <span v-else>Sign In</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    error.value = 'Passwords do not match.'
    return
  }

  if (password.value.length < 6) {
    error.value = 'Password must be at least 6 characters.'
    return
  }

  loading.value = true
  try {
    await auth.setup(username.value, password.value)
    auth.setupCompleted = true
    router.push('/dashboard')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || 'Setup failed. An admin account may already exist.'
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
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || 'Login failed. Please check your credentials.'
  } finally {
    loading.value = false
  }
}
</script>
