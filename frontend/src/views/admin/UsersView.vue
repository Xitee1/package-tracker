<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('users.title') }}</h1>
      <button
        v-if="!showForm"
        @click="showForm = true"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        {{ $t('users.addUser') }}
      </button>
    </div>

    <!-- Add User Form -->
    <div
      v-if="showForm"
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {{ $t('users.createNewUser') }}
      </h2>

      <div
        v-if="formError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ formError }}
      </div>

      <form @submit.prevent="handleCreateUser" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('users.username')
            }}</label>
            <input
              v-model="form.username"
              type="text"
              required
              autocomplete="off"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('users.usernamePlaceholder')"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('users.password')
            }}</label>
            <input
              v-model="form.password"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('users.passwordPlaceholder')"
            />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <input
            id="is_admin"
            v-model="form.is_admin"
            type="checkbox"
            class="h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
          />
          <label for="is_admin" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
            $t('users.adminPrivileges')
          }}</label>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <button
            type="submit"
            :disabled="formSaving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ formSaving ? $t('users.creating') : $t('users.createUser') }}
          </button>
          <button
            type="button"
            @click="closeForm"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            {{ $t('common.cancel') }}
          </button>
        </div>
      </form>
    </div>

    <!-- Users Table -->
    <div
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
    >
      <div v-if="loading" class="p-8 text-center text-gray-500 dark:text-gray-400">
        {{ $t('users.loadingUsers') }}
      </div>

      <div v-else-if="error" class="p-4">
        <div
          class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm"
        >
          {{ error }}
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr
              class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-200 dark:border-gray-700"
            >
              <th class="px-5 py-3">{{ $t('users.id') }}</th>
              <th class="px-5 py-3">{{ $t('users.username') }}</th>
              <th class="px-5 py-3">{{ $t('users.role') }}</th>
              <th class="px-5 py-3 text-right">{{ $t('users.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="user in users"
              :key="user.id"
              class="hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <td class="px-5 py-3 text-sm text-gray-500 dark:text-gray-400">{{ user.id }}</td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-gray-900 dark:text-white">{{
                    user.username
                  }}</span>
                  <span
                    v-if="auth.user?.id === user.id"
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                  >
                    {{ $t('common.you') }}
                  </span>
                </div>
              </td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  :class="
                    user.is_admin
                      ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  "
                >
                  {{ user.is_admin ? $t('common.admin') : $t('common.user') }}
                </span>
              </td>
              <td class="px-5 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="toggleAdmin(user)"
                    :disabled="auth.user?.id === user.id"
                    class="px-3 py-1.5 text-xs font-medium rounded-md border disabled:opacity-40 disabled:cursor-not-allowed"
                    :class="
                      user.is_admin
                        ? 'text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                        : 'text-purple-700 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-800 hover:bg-purple-100 dark:hover:bg-purple-900/50'
                    "
                  >
                    {{ user.is_admin ? $t('users.removeAdmin') : $t('users.makeAdmin') }}
                  </button>
                  <button
                    @click="handleDelete(user)"
                    :disabled="auth.user?.id === user.id"
                    class="px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 bg-white dark:bg-gray-900 border border-red-300 dark:border-red-700 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {{ $t('common.delete') }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="fixed inset-0 bg-black/50" @click="showDeleteConfirm = false"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {{ $t('users.deleteUser') }}
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
          {{ $t('users.deleteConfirm', { username: deleteTarget?.username }) }}
        </p>
        <div class="flex justify-end gap-2">
          <button
            @click="showDeleteConfirm = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            @click="confirmDelete"
            :disabled="deleting"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {{ deleting ? $t('common.deleting') : $t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import api from '@/api/client'
import { getApiErrorMessage } from '@/utils/api-error'

const { t } = useI18n()

interface User {
  id: number
  username: string
  is_admin: boolean
}

const auth = useAuthStore()

const users = ref<User[]>([])
const loading = ref(false)
const error = ref('')

// Form
const showForm = ref(false)
const formError = ref('')
const formSaving = ref(false)
const form = ref({
  username: '',
  password: '',
  is_admin: false,
})

// Delete
const showDeleteConfirm = ref(false)
const deleteTarget = ref<User | null>(null)
const deleting = ref(false)

async function fetchUsers() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/users')
    users.value = res.data
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('users.loadFailed'))
  } finally {
    loading.value = false
  }
}

function closeForm() {
  showForm.value = false
  form.value = { username: '', password: '', is_admin: false }
  formError.value = ''
}

async function handleCreateUser() {
  formError.value = ''
  formSaving.value = true
  try {
    const res = await api.post('/users', form.value)
    users.value.push(res.data)
    closeForm()
  } catch (e: unknown) {
    formError.value = getApiErrorMessage(e, t('users.createFailed'))
  } finally {
    formSaving.value = false
  }
}

async function toggleAdmin(user: User) {
  try {
    const res = await api.patch(`/users/${user.id}`, { is_admin: !user.is_admin })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx !== -1) users.value[idx] = res.data
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('users.updateFailed'))
  }
}

function handleDelete(user: User) {
  deleteTarget.value = user
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`/users/${deleteTarget.value.id}`)
    users.value = users.value.filter((u) => u.id !== deleteTarget.value!.id)
    showDeleteConfirm.value = false
    deleteTarget.value = null
  } catch (e: unknown) {
    error.value = getApiErrorMessage(e, t('users.deleteFailed'))
    showDeleteConfirm.value = false
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
