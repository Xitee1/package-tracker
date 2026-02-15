<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('notifications.title') }}
    </h1>
    <div class="flex flex-col sm:flex-row gap-6">
      <nav class="sm:w-52 flex-shrink-0">
        <div class="flex sm:flex-col gap-1">
          <router-link
            v-for="item in notifierItems"
            :key="item.to"
            :to="item.to"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="
              isActive(item.to)
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            "
          >
            {{ $t(item.label) }}
          </router-link>
        </div>
      </nav>
      <div class="flex-1 min-w-0">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useModulesStore } from '@/stores/modules'
import { getNotifierSidebarItems } from '@/core/moduleRegistry'

const route = useRoute()
const modulesStore = useModulesStore()

const notifierItems = computed(() => {
  return getNotifierSidebarItems().filter(
    (item) => modulesStore.isEnabled(item.moduleKey) && modulesStore.isConfigured(item.moduleKey),
  )
})

function isActive(path: string): boolean {
  return route.path === path
}
</script>
