<template>
  <div class="p-6 max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Settings</h1>

    <!-- Change Password -->
    <div class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Change Password</h2>

      <div v-if="success" class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4">
        {{ success }}
      </div>

      <div v-if="error" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4">
        {{ error }}
      </div>

      <form @submit.prevent="handleChangePassword" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Current Password</label>
          <input
            v-model="form.currentPassword"
            type="password"
            required
            autocomplete="current-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter your current password"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">New Password</label>
          <input
            v-model="form.newPassword"
            type="password"
            required
            autocomplete="new-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter new password"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Confirm New Password</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            required
            autocomplete="new-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Confirm new password"
          />
        </div>

        <div class="pt-2">
          <button
            type="submit"
            :disabled="saving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? 'Updating...' : 'Update Password' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const auth = useAuthStore()

const saving = ref(false)
const error = ref('')
const success = ref('')

const form = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

async function handleChangePassword() {
  error.value = ''
  success.value = ''

  if (form.value.newPassword !== form.value.confirmPassword) {
    error.value = 'New passwords do not match.'
    return
  }

  if (form.value.newPassword.length < 6) {
    error.value = 'New password must be at least 6 characters.'
    return
  }

  saving.value = true
  try {
    await api.patch(`/users/${auth.user!.id}`, {
      password: form.value.newPassword,
      current_password: form.value.currentPassword,
    })
    success.value = 'Password updated successfully.'
    form.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
    setTimeout(() => {
      success.value = ''
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || 'Failed to update password.'
  } finally {
    saving.value = false
  }
}
</script>
