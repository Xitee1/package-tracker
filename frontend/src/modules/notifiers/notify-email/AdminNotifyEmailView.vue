<template>
  <div>
    <ModuleHeader
      :module-key="moduleKey"
      :name="moduleName"
      :description="moduleDescription"
      :enabled="moduleEnabled"
      @update:enabled="moduleEnabled = $event"
    />
    <div :class="{ 'opacity-50 pointer-events-none': !moduleEnabled }">
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      >
        <div
          class="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400 px-4 py-3 rounded-md text-sm"
        >
          {{ $t('modules.notify-email.smtpRequired') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ModuleHeader from '@/components/ModuleHeader.vue'
import { useModulesStore } from '@/stores/modules'

const { t } = useI18n()

const modulesStore = useModulesStore()
const moduleKey = 'notify-email'
const moduleName = computed(() => t('modules.notify-email.title'))
const moduleDescription = computed(() => t('modules.notify-email.description'))
const moduleEnabled = computed({
  get: () => modulesStore.isEnabled(moduleKey),
  set: () => {},
})
</script>
