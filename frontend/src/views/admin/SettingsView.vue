<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('settings.title') }}
    </h1>

    <div class="flex flex-col sm:flex-row gap-6">
      <!-- Vertical Tab Nav -->
      <nav class="sm:w-44 flex-shrink-0">
        <div class="flex sm:flex-col gap-1">
          <router-link
            v-for="tab in tabs"
            :key="tab.to"
            :to="tab.to"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="
              isActive(tab.to)
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
            "
          >
            {{ tab.label }}
          </router-link>
        </div>
      </nav>

      <!-- Tab Content -->
      <div class="flex-1 min-w-0">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()

const tabs = computed(() => [
  { to: '/admin/settings/llm', label: t('settings.llmConfig') },
  { to: '/admin/settings/imap', label: t('settings.imap') },
  { to: '/admin/settings/queue', label: t('settings.queue') },
  { to: '/admin/settings/modules', label: t('settings.modules') },
  { to: '/admin/settings/email', label: t('settings.email') },
])

function isActive(path: string): boolean {
  return route.path === path
}
</script>
