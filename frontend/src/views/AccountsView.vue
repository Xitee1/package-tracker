<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('accounts.title') }}
    </h1>

    <div v-if="!modulesStore.loaded" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>

    <template v-else-if="enabledTabs.length === 0">
      <div
        class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center"
      >
        <p class="text-gray-500 dark:text-gray-400">{{ $t('accounts.noModulesEnabled') }}</p>
      </div>
    </template>

    <template v-else>
      <!-- Tab Navigation -->
      <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav class="flex gap-4">
          <router-link
            v-for="tab in enabledTabs"
            :key="tab.to"
            :to="tab.to"
            class="pb-3 px-1 text-sm font-medium border-b-2 transition-colors"
            :class="
              isActive(tab.to)
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
            "
          >
            {{ tab.label }}
          </router-link>
        </nav>
      </div>

      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useModulesStore } from '@/stores/modules'

const { t } = useI18n()
const route = useRoute()
const modulesStore = useModulesStore()

const allTabs = computed(() => [
  { to: '/accounts/imap', label: t('accounts.tabImap'), module: 'email-imap' },
  { to: '/accounts/forwarding', label: t('accounts.tabForwarding'), module: 'email-global' },
])

const enabledTabs = computed(() =>
  allTabs.value.filter((tab) => modulesStore.isEnabled(tab.module)),
)

function isActive(path: string): boolean {
  return route.path === path
}

onMounted(async () => {
  if (!modulesStore.loaded) {
    await modulesStore.fetchModules()
  }
})
</script>
