<template>
  <div class="p-6 max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">LLM Configuration</h1>

    <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div v-if="loadError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
        {{ loadError }}
      </div>

      <div v-if="loading" class="text-center py-8 text-gray-500">Loading configuration...</div>

      <form v-else @submit.prevent="handleSave" class="space-y-5">
        <div v-if="saveSuccess" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md text-sm">
          Configuration saved successfully.
        </div>

        <div v-if="saveError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {{ saveError }}
        </div>

        <!-- Provider -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Provider</label>
          <div class="flex gap-2">
            <select
              v-model="providerSelect"
              @change="handleProviderChange"
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="ollama">Ollama</option>
              <option value="custom">Custom</option>
            </select>
            <input
              v-if="providerSelect === 'custom'"
              v-model="form.provider"
              type="text"
              required
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter custom provider name"
            />
          </div>
        </div>

        <!-- Model Name -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Model Name</label>
          <input
            v-model="form.model"
            type="text"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="modelPlaceholder"
          />
        </div>

        <!-- API Key -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            API Key
            <span class="text-gray-400 font-normal">(leave blank to keep current)</span>
          </label>
          <input
            v-model="form.api_key"
            type="password"
            autocomplete="new-password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="sk-..."
          />
        </div>

        <!-- API Base URL -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            API Base URL
            <span class="text-gray-400 font-normal">(for Ollama, custom endpoints)</span>
          </label>
          <input
            v-model="form.api_base"
            type="url"
            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="basePlaceholder"
          />
        </div>

        <!-- Buttons -->
        <div class="flex items-center gap-3 pt-2">
          <button
            type="submit"
            :disabled="saving"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? 'Saving...' : 'Save Configuration' }}
          </button>
          <button
            type="button"
            @click="handleTest"
            :disabled="testing"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ testing ? 'Testing...' : 'Test Connection' }}
          </button>
        </div>
      </form>

      <!-- Test Result -->
      <div
        v-if="testResult"
        class="mt-5 px-4 py-3 rounded-md text-sm border"
        :class="testResult.success ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'"
      >
        <p class="font-medium mb-1">{{ testResult.success ? 'Connection Successful' : 'Connection Failed' }}</p>
        <p>{{ testResult.message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

const providerSelect = ref('openai')

const form = ref({
  provider: 'openai',
  model: '',
  api_key: '',
  api_base: '',
})

const knownProviders = ['openai', 'anthropic', 'ollama']

const modelPlaceholder = computed(() => {
  if (providerSelect.value === 'openai') return 'gpt-4o'
  if (providerSelect.value === 'anthropic') return 'claude-sonnet-4-20250514'
  if (providerSelect.value === 'ollama') return 'llama3'
  return 'model-name'
})

const basePlaceholder = computed(() => {
  if (providerSelect.value === 'ollama') return 'http://localhost:11434'
  return 'https://api.example.com/v1'
})

function handleProviderChange() {
  if (providerSelect.value !== 'custom') {
    form.value.provider = providerSelect.value
  } else {
    form.value.provider = ''
  }
}

async function fetchConfig() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/llm/config')
    form.value.provider = res.data.provider || 'openai'
    form.value.model = res.data.model || ''
    form.value.api_key = ''
    form.value.api_base = res.data.api_base || ''

    if (knownProviders.includes(form.value.provider)) {
      providerSelect.value = form.value.provider
    } else {
      providerSelect.value = 'custom'
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    loadError.value = err.response?.data?.detail || 'Failed to load configuration.'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saveError.value = ''
  saveSuccess.value = false
  saving.value = true
  try {
    const payload: Record<string, string> = {
      provider: form.value.provider,
      model: form.value.model,
    }
    if (form.value.api_key) {
      payload.api_key = form.value.api_key
    }
    if (form.value.api_base) {
      payload.api_base = form.value.api_base
    }
    await api.put('/llm/config', payload)
    saveSuccess.value = true
    form.value.api_key = ''
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    saveError.value = err.response?.data?.detail || 'Failed to save configuration.'
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  try {
    const res = await api.post('/llm/test')
    testResult.value = res.data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    testResult.value = {
      success: false,
      message: err.response?.data?.detail || 'Connection test failed.',
    }
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>
