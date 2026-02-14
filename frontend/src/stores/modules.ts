import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

interface Module {
  module_key: string
  enabled: boolean
  configured: boolean
  name: string | null
  type: string | null
  description: string | null
}

export const useModulesStore = defineStore('modules', () => {
  const modules = ref<Module[]>([])
  const loaded = ref(false)

  const isEnabled = computed(() => (key: string) => {
    const m = modules.value.find((mod) => mod.module_key === key)
    return m?.enabled ?? false
  })

  const isConfigured = computed(() => (key: string) => {
    const m = modules.value.find((mod) => mod.module_key === key)
    return m?.configured ?? true
  })

  function getModule(key: string): Module | undefined {
    return modules.value.find((mod) => mod.module_key === key)
  }

  async function fetchModules() {
    const res = await api.get('/modules')
    modules.value = res.data
    loaded.value = true
  }

  return { modules, loaded, isEnabled, isConfigured, getModule, fetchModules }
})
