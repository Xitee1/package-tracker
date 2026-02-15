<template>
  <div>
    <ModuleHeader
      :module-key="moduleKey"
      :name="moduleName"
      :description="moduleDescription"
      :enabled="moduleEnabled"
      @update:enabled="moduleEnabled = $event"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ModuleHeader from '@/components/ModuleHeader.vue'
import { useModulesStore } from '@/stores/modules'

const { t } = useI18n()

const modulesStore = useModulesStore()
const moduleKey = 'notify-webhook'
const moduleName = computed(() => t('modules.notify-webhook.title'))
const moduleDescription = computed(() => t('modules.notify-webhook.description'))
const moduleEnabled = computed({
  get: () => modulesStore.isEnabled(moduleKey),
  set: () => {},
})
</script>
