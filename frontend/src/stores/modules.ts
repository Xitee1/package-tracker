import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

interface Module {
  module_key: string
  enabled: boolean
}

export const useModulesStore = defineStore('modules', () => {
  const modules = ref<Module[]>([])
  const loaded = ref(false)

  const isEnabled = computed(() => (key: string) => {
    const m = modules.value.find((mod) => mod.module_key === key)
    return m?.enabled ?? false
  })

  async function fetchModules() {
    const res = await api.get('/modules')
    modules.value = res.data
    loaded.value = true
  }

  return { modules, loaded, isEnabled, fetchModules }
})
