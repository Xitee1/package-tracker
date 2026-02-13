<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ $t('accounts.title') }}</h1>
      <button
        v-if="!showForm"
        @click="openAddForm"
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
        {{ $t('accounts.addAccount') }}
      </button>
    </div>

    <!-- Add / Edit Form -->
    <div
      v-if="showForm"
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6"
    >
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {{ editingId ? $t('accounts.editAccount') : $t('accounts.addEmailAccount') }}
      </h2>

      <div
        v-if="formError"
        class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm mb-4"
      >
        {{ formError }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('accounts.accountName')
            }}</label>
            <input
              v-model="form.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('accounts.accountNamePlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('accounts.imapHost')
            }}</label>
            <input
              v-model="form.imap_host"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('accounts.imapHostPlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('accounts.imapPort')
            }}</label>
            <input
              v-model.number="form.imap_port"
              type="number"
              required
              min="1"
              max="65535"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('accounts.username')
            }}</label>
            <input
              v-model="form.imap_user"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('accounts.usernamePlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {{ $t('accounts.password') }}
              <span v-if="editingId" class="text-gray-400 dark:text-gray-500 font-normal">{{
                $t('accounts.passwordKeepCurrent')
              }}</span>
            </label>
            <input
              v-model="form.imap_password"
              type="password"
              :required="!editingId"
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :placeholder="$t('accounts.passwordPlaceholder')"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{
              $t('accounts.pollingInterval')
            }}</label>
            <input
              v-model.number="form.polling_interval_sec"
              type="number"
              required
              min="30"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <div class="flex items-center gap-2">
          <input
            id="use_ssl"
            v-model="form.use_ssl"
            type="checkbox"
            class="h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500"
          />
          <label for="use_ssl" class="text-sm font-medium text-gray-700 dark:text-gray-300">{{
            $t('accounts.useSsl')
          }}</label>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <button
            type="submit"
            :disabled="formSaving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{
              formSaving
                ? $t('common.saving')
                : editingId
                  ? $t('accounts.updateAccount')
                  : $t('accounts.createAccount')
            }}
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

    <!-- Loading -->
    <div v-if="accountsStore.loading" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ $t('accounts.loadingAccounts') }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="accountsStore.accounts.length === 0 && !showForm"
      class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center"
    >
      <svg
        class="mx-auto w-12 h-12 text-gray-300 dark:text-gray-600 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.5"
          d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-1">
        {{ $t('accounts.noAccounts') }}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {{ $t('accounts.noAccountsHint') }}
      </p>
      <button
        @click="openAddForm"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 4v16m8-8H4"
          />
        </svg>
        {{ $t('accounts.addAccount') }}
      </button>
    </div>

    <!-- Account Cards -->
    <div v-else class="space-y-4">
      <div
        v-for="account in accountsStore.accounts"
        :key="account.id"
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700"
      >
        <!-- Account Header -->
        <div class="p-5">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-3 mb-1">
                <h3 class="text-base font-semibold text-gray-900 dark:text-white truncate">
                  {{ account.name }}
                </h3>
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                  :class="
                    account.is_active
                      ? 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  "
                >
                  {{ account.is_active ? $t('common.active') : $t('common.inactive') }}
                </span>
              </div>
              <div
                class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 text-sm text-gray-500 dark:text-gray-400"
              >
                <span class="flex items-center gap-1">
                  <svg
                    class="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"
                    />
                  </svg>
                  {{ account.imap_host }}:{{ account.imap_port }}
                </span>
                <span class="flex items-center gap-1">
                  <svg
                    class="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  {{ account.imap_user }}
                </span>
                <span v-if="account.use_ssl" class="flex items-center gap-1">
                  <svg
                    class="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                    />
                  </svg>
                  {{ $t('common.ssl') }}
                </span>
              </div>
            </div>

            <div class="flex items-center gap-2 ml-4 flex-shrink-0">
              <button
                @click="handleTest(account.id)"
                :disabled="testingId === account.id"
                class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                :title="$t('common.test')"
              >
                {{ testingId === account.id ? $t('common.testing') : $t('common.test') }}
              </button>
              <button
                @click="openEditForm(account)"
                class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                {{ $t('common.edit') }}
              </button>
              <button
                @click="handleDelete(account)"
                :disabled="deletingId === account.id"
                class="px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 bg-white dark:bg-gray-800 border border-red-300 dark:border-red-700 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50"
              >
                {{ deletingId === account.id ? $t('common.deleting') : $t('common.delete') }}
              </button>
              <button
                @click="toggleExpand(account.id)"
                class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                :title="$t('accounts.manageFolders')"
              >
                <svg
                  class="w-5 h-5 transition-transform duration-200"
                  :class="{ 'rotate-180': expandedId === account.id }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Test Result -->
          <div
            v-if="testResults[account.id]"
            class="mt-3 px-3 py-2 rounded-md text-sm"
            :class="
              testResults[account.id]!.success
                ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-200 dark:border-green-800'
                : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800'
            "
          >
            {{ testResults[account.id]!.message }}
          </div>
        </div>

        <!-- Expanded Folder Management -->
        <div
          v-if="expandedId === account.id"
          class="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-5"
        >
          <div class="flex items-center justify-between mb-4">
            <h4 class="text-sm font-semibold text-gray-900 dark:text-white">
              {{ $t('accounts.folderManagement') }}
            </h4>
            <button
              @click="loadFolders(account.id)"
              :disabled="foldersLoading"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/50 disabled:opacity-50"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              {{ foldersLoading ? $t('accounts.loadingFolders') : $t('accounts.loadFolders') }}
            </button>
          </div>

          <div
            v-if="folderError"
            class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-3 py-2 rounded-md text-sm mb-4"
          >
            {{ folderError }}
          </div>

          <div
            v-if="availableFolders.length === 0 && !foldersLoading"
            class="text-sm text-gray-400 dark:text-gray-500 italic py-2"
          >
            {{ $t('accounts.loadFoldersHint') }}
          </div>
          <div v-else-if="foldersLoading" class="text-sm text-gray-400 dark:text-gray-500 py-2">
            {{ $t('accounts.loadingFolders') }}
          </div>
          <div v-else class="space-y-1 max-h-72 overflow-y-auto">
            <div
              v-for="folder in availableFolders"
              :key="folder.name"
              class="flex items-center justify-between bg-white dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 px-3 py-2"
            >
              <span class="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <svg
                  class="w-4 h-4 flex-shrink-0"
                  :class="
                    isWatched(folder.name) ? 'text-blue-500' : 'text-gray-400 dark:text-gray-500'
                  "
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
                {{ folder.name }}
              </span>
              <div class="flex items-center gap-2">
                <template v-if="isWatched(folder.name)">
                  <input
                    type="number"
                    min="1"
                    :value="getWatchedFolder(folder.name)?.max_email_age_days ?? ''"
                    :placeholder="$t('accounts.ageDaysOverride')"
                    class="w-16 px-1.5 py-1 border border-gray-300 dark:border-gray-600 rounded text-xs bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 text-center"
                    @change="
                      handleOverrideChange(account.id, folder.name, 'max_email_age_days', $event)
                    "
                  />
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{
                    $t('accounts.ageDaysOverride')
                  }}</span>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    :value="getWatchedFolder(folder.name)?.processing_delay_sec ?? ''"
                    :placeholder="$t('accounts.delaySecOverride')"
                    class="w-16 px-1.5 py-1 border border-gray-300 dark:border-gray-600 rounded text-xs bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 text-center"
                    @change="
                      handleOverrideChange(account.id, folder.name, 'processing_delay_sec', $event)
                    "
                  />
                  <span class="text-xs text-gray-400 dark:text-gray-500">{{
                    $t('accounts.delaySecOverride')
                  }}</span>
                  <button
                    @click="handleUnwatch(account.id, folder.name)"
                    class="text-xs font-medium text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors"
                  >
                    {{ $t('common.remove') }}
                  </button>
                </template>
                <button
                  v-else
                  @click="handleAddWatched(account.id, folder.name)"
                  class="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium transition-colors"
                >
                  {{ $t('common.watch') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="fixed inset-0 bg-black/50" @click="showDeleteConfirm = false"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {{ $t('accounts.deleteAccount') }}
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
          {{ $t('accounts.deleteConfirm', { name: deleteTarget?.name }) }}
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
            :disabled="deletingId !== null"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {{ $t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  useAccountsStore,
  type EmailAccount,
  type IMAPFolder,
  type WatchedFolder,
} from '@/stores/accounts'

const { t } = useI18n()
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
  imap_user: '',
  imap_password: '',
  use_ssl: true,
  polling_interval_sec: 300,
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
    imap_user: '',
    imap_password: '',
    use_ssl: true,
    polling_interval_sec: 300,
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
    imap_user: account.imap_user,
    imap_password: '',
    use_ssl: account.use_ssl,
    polling_interval_sec: account.polling_interval_sec,
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
        imap_user: form.value.imap_user,
        use_ssl: form.value.use_ssl,
        polling_interval_sec: form.value.polling_interval_sec,
      }
      if (form.value.imap_password) {
        data.imap_password = form.value.imap_password
      }
      await accountsStore.updateAccount(editingId.value, data)
    } else {
      await accountsStore.createAccount(form.value)
    }
    closeForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || t('accounts.saveFailed')
  } finally {
    formSaving.value = false
  }
}

async function handleTest(id: number) {
  testingId.value = id
  delete testResults.value[id]
  try {
    const result = await accountsStore.testConnection(id)
    testResults.value[id] = {
      success: result.success,
      message: result.success
        ? t('accounts.connectionTestSuccess')
        : t('accounts.connectionTestFailed'),
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    testResults.value[id] = {
      success: false,
      message: err.response?.data?.detail || t('accounts.connectionTestFailed'),
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
    formError.value = err.response?.data?.detail || t('accounts.deleteFailed')
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
  watchedFolders.value = []
  folderError.value = ''
  await loadFolders(id)
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
    folderError.value = err.response?.data?.detail || t('accounts.loadFoldersFailed')
  } finally {
    foldersLoading.value = false
  }
}

function isWatched(folderName: string): boolean {
  return watchedFolders.value.some((wf) => wf.folder_path === folderName)
}

function getWatchedFolder(folderName: string): WatchedFolder | undefined {
  return watchedFolders.value.find((wf) => wf.folder_path === folderName)
}

async function handleOverrideChange(
  accountId: number,
  folderName: string,
  field: string,
  event: Event,
) {
  const wf = getWatchedFolder(folderName)
  if (!wf) return
  const input = event.target as HTMLInputElement
  const value = input.value === '' ? null : Number(input.value)
  try {
    const updated = await accountsStore.updateWatchedFolder(accountId, wf.id, { [field]: value })
    const idx = watchedFolders.value.findIndex((f) => f.id === wf.id)
    if (idx !== -1) watchedFolders.value[idx] = updated
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    folderError.value = err.response?.data?.detail || t('accounts.overrideUpdateFailed')
  }
}

async function handleAddWatched(accountId: number, folderName: string) {
  try {
    const wf = await accountsStore.addWatchedFolder(accountId, folderName)
    watchedFolders.value.push(wf)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    folderError.value = err.response?.data?.detail || t('accounts.addWatchedFailed')
  }
}

async function handleRemoveWatched(accountId: number, folderId: number) {
  try {
    await accountsStore.removeWatchedFolder(accountId, folderId)
    watchedFolders.value = watchedFolders.value.filter((wf) => wf.id !== folderId)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    folderError.value = err.response?.data?.detail || t('accounts.removeWatchedFailed')
  }
}

async function handleUnwatch(accountId: number, folderName: string) {
  const wf = watchedFolders.value.find((w) => w.folder_path === folderName)
  if (wf) {
    await handleRemoveWatched(accountId, wf.id)
  }
}

onMounted(() => {
  accountsStore.fetchAccounts()
})
</script>
