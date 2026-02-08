<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">System Status</h1>
      <button
        @click="fetchStatus"
        :disabled="loading"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50"
      >
        <svg
          class="w-4 h-4"
          :class="{ 'animate-spin': loading }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>

    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-6">
      {{ error }}
    </div>

    <div v-if="loading && !status" class="text-center py-12 text-gray-500">Loading system status...</div>

    <template v-if="status">
      <!-- Overview Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm font-medium text-gray-500">Total Workers</p>
          <p class="text-2xl font-bold text-gray-900 mt-1">{{ workers.length }}</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm font-medium text-gray-500">Running</p>
          <p class="text-2xl font-bold text-green-600 mt-1">{{ runningCount }}</p>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <p class="text-sm font-medium text-gray-500">Errors</p>
          <p class="text-2xl font-bold mt-1" :class="errorCount > 0 ? 'text-red-600' : 'text-gray-400'">
            {{ errorCount }}
          </p>
        </div>
      </div>

      <!-- Workers Table -->
      <div class="bg-white rounded-lg shadow-sm border border-gray-200">
        <div class="px-5 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">IMAP Workers</h2>
        </div>

        <div v-if="workers.length === 0" class="p-8 text-center text-gray-500 text-sm">
          No IMAP workers are configured. Add email accounts and watched folders to start workers.
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                <th class="px-5 py-3">Folder ID</th>
                <th class="px-5 py-3">Status</th>
                <th class="px-5 py-3">Errors</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="worker in workers" :key="worker.folder_id" class="hover:bg-gray-50">
                <td class="px-5 py-3 text-sm font-medium text-gray-900">{{ worker.folder_id }}</td>
                <td class="px-5 py-3">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
                    :class="worker.running ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'"
                  >
                    <span
                      class="w-1.5 h-1.5 rounded-full"
                      :class="worker.running ? 'bg-green-500' : 'bg-gray-400'"
                    ></span>
                    {{ worker.running ? 'Running' : 'Stopped' }}
                  </span>
                </td>
                <td class="px-5 py-3">
                  <span v-if="!worker.error" class="text-sm text-gray-400">None</span>
                  <span v-else class="text-sm text-red-600">{{ worker.error }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

interface WorkerStatus {
  folder_id: number
  running: boolean
  error: string | null
}

interface SystemStatus {
  workers: WorkerStatus[]
}

const status = ref<SystemStatus | null>(null)
const loading = ref(false)
const error = ref('')

const workers = computed(() => status.value?.workers ?? [])
const runningCount = computed(() => workers.value.filter((w) => w.running).length)
const errorCount = computed(() => workers.value.filter((w) => w.error).length)

async function fetchStatus() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/system/status')
    status.value = res.data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || 'Failed to load system status.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatus()
})
</script>
