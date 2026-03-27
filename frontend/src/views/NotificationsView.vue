<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('notifications.title') }}
    </h1>
    <div class="flex flex-col sm:flex-row gap-6">
      <!-- Mobile: dropdown navigation -->
      <div class="sm:hidden">
        <div class="relative">
          <button
            @click="dropdownOpen = !dropdownOpen"
            @keydown.esc.window="dropdownOpen = false"
            :aria-expanded="dropdownOpen"
            aria-haspopup="true"
            class="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white"
          >
            <span>{{ currentLabel }}</span>
            <svg
              class="w-4 h-4 transition-transform duration-200"
              :class="{ 'rotate-180': dropdownOpen }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div
            v-if="dropdownOpen"
            class="absolute z-20 left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 max-h-64 overflow-y-auto"
          >
            <router-link
              v-for="item in notifierItems"
              :key="item.to"
              :to="item.to"
              class="block px-3 py-2 text-sm transition-colors"
              :class="isActive(item.to) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
            >
              {{ $t(item.label) }}
            </router-link>
          </div>
        </div>
        <div v-if="dropdownOpen" class="fixed inset-0 z-10" @click="dropdownOpen = false"></div>
      </div>

      <!-- Desktop: vertical sidebar -->
      <nav class="hidden sm:block sm:w-52 flex-shrink-0">
        <div class="flex flex-col gap-1">
          <router-link
            v-for="item in notifierItems"
            :key="item.to"
            :to="item.to"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="isActive(item.to) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
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
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useModulesStore } from '@/stores/modules'
import { getNotifierSidebarItems } from '@/core/moduleRegistry'

const { t } = useI18n()
const route = useRoute()
const modulesStore = useModulesStore()

const dropdownOpen = ref(false)

const notifierItems = computed(() => {
  return getNotifierSidebarItems().filter(
    (item) => modulesStore.isEnabled(item.moduleKey) && modulesStore.isConfigured(item.moduleKey),
  )
})

const currentLabel = computed(() => {
  const item = notifierItems.value.find((i) => route.path === i.to)
  return item ? t(item.label) : t('notifications.title')
})

watch(() => route.path, () => {
  dropdownOpen.value = false
})

function isActive(path: string): boolean {
  return route.path === path
}
</script>
