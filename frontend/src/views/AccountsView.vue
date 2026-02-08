<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Email Accounts</h1>
      <button
        v-if="!showForm"
        @click="openAddForm"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Account
      </button>
    </div>

    <!-- Add / Edit Form -->
    <div v-if="showForm" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">
        {{ editingId ? 'Edit Account' : 'Add Email Account' }}
      </h2>

      <div v-if="formError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
        {{ formError }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Account Name</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g. Personal Gmail"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">IMAP Host</label>
            <input
              v-model="form.imap_host"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="imap.gmail.com"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">IMAP Port</label>
            <input
              v-model.number="form.imap_port"
              type="number"
              required
              min="1"
              max="65535"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              v-model="form.username"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="user@gmail.com"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Password
              <span v-if="editingId" class="text-gray-400 font-normal">(leave blank to keep current)</span>
            </label>
            <input
              v-model="form.password"
              type="password"
              :required="!editingId"
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="App password or IMAP password"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Polling Interval (seconds)</label>
            <input
              v-model.number="form.polling_interval"
              type="number"
              required
              min="30"
              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <input
            id="use_ssl"
            v-model="form.use_ssl"
            type="checkbox"
            class="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label for="use_ssl" class="text-sm font-medium text-gray-700">Use SSL/TLS</label>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <button
            type="submit"
            :disabled="formSaving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ formSaving ? 'Saving...' : editingId ? 'Update Account' : 'Create Account' }}
          </button>
          <button
            type="button"
            @click="closeForm"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>

    <!-- Loading -->
    <div v-if="accountsStore.loading" class="text-center py-12 text-gray-500">
      Loading email accounts...
    </div>

    <!-- Empty State -->
    <div
      v-else-if="accountsStore.accounts.length === 0 && !showForm"
      class="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center"
    >
      <svg class="mx-auto w-12 h-12 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.5"
          d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-1">No email accounts</h3>
      <p class="text-sm text-gray-500 mb-4">
        Add an email account to start tracking packages from your inbox.
      </p>
      <button
        @click="openAddForm"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Account
      </button>
    </div>

    <!-- Account Cards -->
    <div v-else class="space-y-4">
      <div
        v-for="account in accountsStore.accounts"
        :key="account.id"
        class="bg-white rounded-lg shadow-sm border border-gray-200"
      >
        <!-- Account Header -->
        <div class="p-5">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-3 mb-1">
                <h3 class="text-base font-semibold text-gray-900 truncate">{{ account.name }}</h3>
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="account.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'"
                >
                  {{ account.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <div class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 text-sm text-gray-500">
                <span class="flex items-center gap-1">
                  <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
                  </svg>
                  {{ account.imap_host }}:{{ account.imap_port }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  {{ account.username }}
                </span>
                <span v-if="account.use_ssl" class="flex items-center gap-1">
                  <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  SSL
                </span>
              </div>
            </div>

            <div class="flex items-center gap-2 ml-4 flex-shrink-0">
              <button
                @click="handleTest(account.id)"
                :disabled="testingId === account.id"
                class="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                title="Test Connection"
              >
                {{ testingId === account.id ? 'Testing...' : 'Test' }}
              </button>
              <button
                @click="openEditForm(account)"
                class="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Edit
              </button>
              <button
                @click="handleDelete(account)"
                :disabled="deletingId === account.id"
                class="px-3 py-1.5 text-xs font-medium text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50 disabled:opacity-50"
              >
                {{ deletingId === account.id ? 'Deleting...' : 'Delete' }}
              </button>
              <button
                @click="toggleExpand(account.id)"
                class="p-1.5 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
                title="Manage folders"
              >
                <svg
                  class="w-5 h-5 transition-transform duration-200"
                  :class="{ 'rotate-180': expandedId === account.id }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Test Result -->
          <div
            v-if="testResults[account.id]"
            class="mt-3 px-3 py-2 rounded-md text-sm"
            :class="testResults[account.id]!.success ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'"
          >
            {{ testResults[account.id]!.message }}
          </div>
        </div>

        <!-- Expanded Folder Management -->
        <div v-if="expandedId === account.id" class="border-t border-gray-200 bg-gray-50 p-5">
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-sm font-semibold text-gray-900">Folder Management</h4>
            <button
              @click="loadFolders(account.id)"
              :disabled="foldersLoading"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 disabled:opacity-50"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {{ foldersLoading ? 'Loading...' : 'Load Folders' }}
            </button>
          </div>

          <div v-if="folderError" class="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm mb-4">
            {{ folderError }}
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Watched Folders -->
            <div>
              <h5 class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Watched Folders</h5>
              <div v-if="watchedFolders.length === 0" class="text-sm text-gray-400 italic py-2">
                No folders being watched.
              </div>
              <div v-else class="space-y-1">
                <div
                  v-for="wf in watchedFolders"
                  :key="wf.id"
                  class="flex items-center justify-between bg-white rounded-md border border-gray-200 px-3 py-2"
                >
                  <span class="text-sm text-gray-700 flex items-center gap-2">
                    <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    {{ wf.folder_name }}
                  </span>
                  <button
                    @click="handleRemoveWatched(account.id, wf.folder_name)"
                    class="text-xs text-red-600 hover:text-red-800 font-medium"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>

            <!-- Available Folders -->
            <div>
              <h5 class="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Available IMAP Folders</h5>
              <div v-if="availableFolders.length === 0 && !foldersLoading" class="text-sm text-gray-400 italic py-2">
                Click "Load Folders" to fetch available folders.
              </div>
              <div v-else-if="foldersLoading" class="text-sm text-gray-400 py-2">
                Loading folders...
              </div>
              <div v-else class="space-y-1 max-h-64 overflow-y-auto">
                <div
                  v-for="folder in availableFolders"
                  :key="folder.name"
                  class="flex items-center justify-between bg-white rounded-md border border-gray-200 px-3 py-2"
                >
                  <span class="text-sm text-gray-700 flex items-center gap-2">
                    <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    {{ folder.name }}
                  </span>
                  <button
                    v-if="!isWatched(folder.name)"
                    @click="handleAddWatched(account.id, folder.name)"
                    class="text-xs text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Watch
                  </button>
                  <span v-else class="text-xs text-green-600 font-medium flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    Watched
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="fixed inset-0 bg-black/50" @click="showDeleteConfirm = false"></div>
      <div class="relative bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Delete Account</h3>
        <p class="text-sm text-gray-600 mb-6">
          Are you sure you want to delete "{{ deleteTarget?.name }}"? This will also remove all watched folder settings.
        </p>
        <div class="flex justify-end gap-2">
          <button
            @click="showDeleteConfirm = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            @click="confirmDelete"
            :disabled="deletingId !== null"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAccountsStore, type EmailAccount, type IMAPFolder, type WatchedFolder } from '@/stores/accounts'

const accountsStore = useAccountsStore()

// Form state
const showForm = ref(false)
const editingId = ref<number | null>(null)
const formSaving = ref(false)
const formError = ref('')

const form = ref({
  name: '',
  imap_host: '',
  imap_port: 993,
  username: '',
  password: '',
  use_ssl: true,
  polling_interval: 300,
})

// Test connection state
const testingId = ref<number | null>(null)
const testResults = ref<Record<number, { success: boolean; message: string }>>({})

// Delete state
const showDeleteConfirm = ref(false)
const deleteTarget = ref<EmailAccount | null>(null)
const deletingId = ref<number | null>(null)

// Folder management state
const expandedId = ref<number | null>(null)
const availableFolders = ref<IMAPFolder[]>([])
const watchedFolders = ref<WatchedFolder[]>([])
const foldersLoading = ref(false)
const folderError = ref('')

function resetForm() {
  form.value = {
    name: '',
    imap_host: '',
    imap_port: 993,
    username: '',
    password: '',
    use_ssl: true,
    polling_interval: 300,
  }
  formError.value = ''
  editingId.value = null
}

function openAddForm() {
  resetForm()
  showForm.value = true
}

function openEditForm(account: EmailAccount) {
  editingId.value = account.id
  form.value = {
    name: account.name,
    imap_host: account.imap_host,
    imap_port: account.imap_port,
    username: account.username,
    password: '',
    use_ssl: account.use_ssl,
    polling_interval: account.polling_interval,
  }
  formError.value = ''
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  resetForm()
}

async function handleSubmit() {
  formError.value = ''
  formSaving.value = true
  try {
    if (editingId.value) {
      const data: Record<string, unknown> = {
        name: form.value.name,
        imap_host: form.value.imap_host,
        imap_port: form.value.imap_port,
        username: form.value.username,
        use_ssl: form.value.use_ssl,
        polling_interval: form.value.polling_interval,
      }
      if (form.value.password) {
        data.password = form.value.password
      }
      await accountsStore.updateAccount(editingId.value, data)
    } else {
      await accountsStore.createAccount(form.value)
    }
    closeForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || 'Failed to save account.'
  } finally {
    formSaving.value = false
  }
}

async function handleTest(id: number) {
  testingId.value = id
  delete testResults.value[id]
  try {
    const result = await accountsStore.testConnection(id)
    testResults.value[id] = result
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    testResults.value[id] = {
      success: false,
      message: err.response?.data?.detail || 'Connection test failed.',
    }
  } finally {
    testingId.value = null
  }
}

function handleDelete(account: EmailAccount) {
  deleteTarget.value = account
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deletingId.value = deleteTarget.value.id
  try {
    await accountsStore.deleteAccount(deleteTarget.value.id)
    showDeleteConfirm.value = false
    deleteTarget.value = null
    if (expandedId.value === deletingId.value) {
      expandedId.value = null
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || 'Failed to delete account.'
  } finally {
    deletingId.value = null
  }
}

async function toggleExpand(id: number) {
  if (expandedId.value === id) {
    expandedId.value = null
    return
  }
  expandedId.value = id
  availableFolders.value = []
  folderError.value = ''
  // Load watched folders automatically
  try {
    watchedFolders.value = await accountsStore.fetchWatchedFolders(id)
  } catch {
    watchedFolders.value = []
  }
}

async function loadFolders(id: number) {
  foldersLoading.value = true
  folderError.value = ''
  try {
    const [folders, watched] = await Promise.all([
      accountsStore.fetchFolders(id),
      accountsStore.fetchWatchedFolders(id),
    ])
    availableFolders.value = folders
    watchedFolders.value = watched
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    folderError.value = err.response?.data?.detail || 'Failed to load folders. Check account connection.'
  } finally {
    foldersLoading.value = false
  }
}

function isWatched(folderName: string): boolean {
  return watchedFolders.value.some((wf) => wf.folder_name === folderName)
}

async function handleAddWatched(accountId: number, folderName: string) {
  try {
    const wf = await accountsStore.addWatchedFolder(accountId, folderName)
    watchedFolders.value.push(wf)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    folderError.value = err.response?.data?.detail || 'Failed to add watched folder.'
  }
}

async function handleRemoveWatched(accountId: number, folderName: string) {
  try {
    await accountsStore.removeWatchedFolder(accountId, folderName)
    watchedFolders.value = watchedFolders.value.filter((wf) => wf.folder_name !== folderName)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    folderError.value = err.response?.data?.detail || 'Failed to remove watched folder.'
  }
}

onMounted(() => {
  accountsStore.fetchAccounts()
})
</script>
