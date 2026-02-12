<template>
  <div class="p-6 max-w-2xl mx-auto space-y-6">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Profile</h1>

    <!-- Change Password -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Change Password</h2>

      <div
        v-if="pwSuccess"
        class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ pwSuccess }}
      </div>

      <div
        v-if="pwError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ pwError }}
      </div>

      <form @submit.prevent="handleChangePassword" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >Current Password</label
          >
          <input
            v-model="pwForm.currentPassword"
            type="password"
            required
            autocomplete="current-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter your current password"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >New Password</label
          >
          <input
            v-model="pwForm.newPassword"
            type="password"
            required
            autocomplete="new-password"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter new password"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >Confirm New Password</label
          >
          <input
            v-model="pwForm.confirmPassword"
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
            :disabled="pwSaving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ pwSaving ? 'Updating...' : 'Update Password' }}
          </button>
        </div>
      </form>
    </div>

    <!-- API Keys -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
    >
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">API Keys</h2>
        <span class="text-sm text-gray-500 dark:text-gray-400">{{ apiKeys.length }} / 25</span>
      </div>

      <!-- Newly created key alert -->
      <div
        v-if="newlyCreatedKey"
        class="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 px-4 py-3 rounded-md text-sm mb-4"
      >
        <p class="font-medium text-amber-800 dark:text-amber-300 mb-2">
          Copy your API key now. It won't be shown again.
        </p>
        <div class="flex items-center gap-2">
          <code
            class="flex-1 bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700 rounded px-3 py-1.5 text-xs font-mono text-gray-900 dark:text-white select-all break-all"
          >{{ newlyCreatedKey }}</code>
          <button
            @click="copyKey"
            class="shrink-0 px-3 py-1.5 text-xs font-medium rounded border border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/50"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
        <button
          @click="newlyCreatedKey = ''"
          class="mt-2 text-xs text-amber-600 dark:text-amber-400 hover:underline"
        >
          Dismiss
        </button>
      </div>

      <div
        v-if="keyError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ keyError }}
      </div>

      <!-- Create key form -->
      <div v-if="showCreateForm" class="flex items-end gap-2 mb-4">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >Key Name</label
          >
          <input
            v-model="newKeyName"
            type="text"
            maxlength="64"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g. Home Assistant"
            @keyup.enter="handleCreateKey"
          />
        </div>
        <button
          @click="handleCreateKey"
          :disabled="!newKeyName.trim() || keyCreating"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ keyCreating ? 'Creating...' : 'Create' }}
        </button>
        <button
          @click="showCreateForm = false; newKeyName = ''"
          class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          Cancel
        </button>
      </div>
      <div v-else class="mb-4">
        <button
          @click="showCreateForm = true"
          :disabled="apiKeys.length >= 25"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Create API Key
        </button>
      </div>

      <!-- Keys table -->
      <div v-if="apiKeys.length > 0" class="border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th class="text-left px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Name</th>
              <th class="text-left px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Key</th>
              <th class="text-left px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Created</th>
              <th class="text-left px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Last Used</th>
              <th class="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-for="k in apiKeys" :key="k.id">
              <td class="px-4 py-2 text-gray-900 dark:text-white">{{ k.name }}</td>
              <td class="px-4 py-2">
                <code class="text-xs text-gray-500 dark:text-gray-400">{{ k.key_prefix }}...</code>
              </td>
              <td class="px-4 py-2 text-gray-500 dark:text-gray-400">{{ formatDate(k.created_at) }}</td>
              <td class="px-4 py-2 text-gray-500 dark:text-gray-400">{{ k.last_used_at ? formatDate(k.last_used_at) : 'Never' }}</td>
              <td class="px-4 py-2 text-right">
                <button
                  @click="handleDeleteKey(k.id)"
                  class="text-xs text-red-600 dark:text-red-400 hover:underline"
                >
                  {{ confirmDeleteId === k.id ? 'Confirm?' : 'Delete' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="text-sm text-gray-500 dark:text-gray-400">No API keys yet.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'

const auth = useAuthStore()

// --- Password section ---
const pwSaving = ref(false)
const pwError = ref('')
const pwSuccess = ref('')
const pwForm = ref({ currentPassword: '', newPassword: '', confirmPassword: '' })

async function handleChangePassword() {
  pwError.value = ''
  pwSuccess.value = ''
  if (pwForm.value.newPassword !== pwForm.value.confirmPassword) {
    pwError.value = 'New passwords do not match.'
    return
  }
  if (pwForm.value.newPassword.length < 6) {
    pwError.value = 'New password must be at least 6 characters.'
    return
  }
  pwSaving.value = true
  try {
    await api.patch(`/users/${auth.user!.id}`, {
      password: pwForm.value.newPassword,
      current_password: pwForm.value.currentPassword,
    })
    pwSuccess.value = 'Password updated successfully.'
    pwForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' }
    setTimeout(() => { pwSuccess.value = '' }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    pwError.value = err.response?.data?.detail || 'Failed to update password.'
  } finally {
    pwSaving.value = false
  }
}

// --- API Keys section ---
interface ApiKeyItem {
  id: number
  name: string
  key_prefix: string
  created_at: string
  expires_at: string
  last_used_at: string | null
}

const apiKeys = ref<ApiKeyItem[]>([])
const showCreateForm = ref(false)
const newKeyName = ref('')
const keyCreating = ref(false)
const keyError = ref('')
const newlyCreatedKey = ref('')
const copied = ref(false)
const confirmDeleteId = ref<number | null>(null)
let confirmTimer: ReturnType<typeof setTimeout> | null = null

async function fetchKeys() {
  try {
    const { data } = await api.get('/api-keys')
    apiKeys.value = data
  } catch {
    keyError.value = 'Failed to load API keys.'
  }
}

async function handleCreateKey() {
  if (!newKeyName.value.trim()) return
  keyCreating.value = true
  keyError.value = ''
  try {
    const { data } = await api.post('/api-keys', { name: newKeyName.value.trim() })
    newlyCreatedKey.value = data.key
    copied.value = false
    newKeyName.value = ''
    showCreateForm.value = false
    await fetchKeys()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    keyError.value = err.response?.data?.detail || 'Failed to create API key.'
  } finally {
    keyCreating.value = false
  }
}

async function handleDeleteKey(id: number) {
  if (confirmDeleteId.value !== id) {
    confirmDeleteId.value = id
    if (confirmTimer) clearTimeout(confirmTimer)
    confirmTimer = setTimeout(() => { confirmDeleteId.value = null }, 3000)
    return
  }
  confirmDeleteId.value = null
  try {
    await api.delete(`/api-keys/${id}`)
    await fetchKeys()
  } catch {
    keyError.value = 'Failed to delete API key.'
  }
}

function copyKey() {
  navigator.clipboard.writeText(newlyCreatedKey.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

onMounted(fetchKeys)
</script>
