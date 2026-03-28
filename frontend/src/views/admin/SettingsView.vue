<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('settings.title') }}
    </h1>

    <div class="flex flex-col sm:flex-row gap-6">
      <!-- Mobile: dropdown navigation -->
      <div class="sm:hidden">
        <MobileNavDropdown :label="currentLabel">
          <router-link
            v-for="item in coreItems"
            :key="item.name"
            :to="{ name: item.name }"
            class="block px-3 py-2 text-sm transition-colors"
            :class="isActive(item.name) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
          >
            {{ $t(item.labelKey) }}
          </router-link>
          <template v-for="group in sidebarGroups" :key="group.group">
            <div class="px-3 py-1.5 mt-1 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider border-t border-gray-100 dark:border-gray-700">
              {{ $t('system.moduleType.' + group.group) }}
            </div>
            <router-link
              v-for="groupItem in group.items"
              :key="groupItem.to"
              :to="groupItem.to"
              class="block px-3 py-2 text-sm transition-colors"
              :class="isActiveByPath(groupItem.to) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
            >
              {{ $t(groupItem.label) }}
            </router-link>
          </template>
        </MobileNavDropdown>
      </div>

      <!-- Desktop: vertical tab nav with collapsible groups -->
      <nav class="hidden sm:block sm:w-52 flex-shrink-0">
        <div class="flex flex-col gap-1">
          <router-link
            v-for="item in coreItems"
            :key="item.name"
            :to="{ name: item.name }"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="isActive(item.name) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
          >
            {{ $t(item.labelKey) }}
          </router-link>

          <template v-for="group in sidebarGroups" :key="group.group">
            <button
              @click="toggleGroup(group.group)"
              class="flex items-center justify-between w-full px-3 py-2 mt-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300"
            >
              {{ $t('system.moduleType.' + group.group) }}
              <svg
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': !collapsedGroups[group.group] }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            <template v-if="!collapsedGroups[group.group]">
              <router-link
                v-for="item in group.items"
                :key="item.to"
                :to="item.to"
                class="px-3 py-2 pl-5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap block"
                :class="isActiveByPath(item.to) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
              >
                {{ $t(item.label) }}
              </router-link>
            </template>
          </template>
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
import { reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getAdminSidebarItems } from '@/core/moduleRegistry'
import MobileNavDropdown from '@/components/MobileNavDropdown.vue'

const { t } = useI18n()
const route = useRoute()

const sidebarGroups = getAdminSidebarItems()
const collapsedGroups = reactive<Record<string, boolean>>({})

const coreItems = [
  { name: 'queue-settings', labelKey: 'settings.queue' },
  { name: 'analysers-settings', labelKey: 'settings.analysers' },
  { name: 'smtp-settings', labelKey: 'settings.smtp' },
]

const currentLabel = computed(() => {
  const coreItem = coreItems.find((item) => route.name === item.name)
  if (coreItem) return t(coreItem.labelKey)
  for (const group of sidebarGroups) {
    for (const item of group.items) {
      if (route.path === item.to) return t(item.label)
    }
  }
  return t('settings.title')
})

function toggleGroup(group: string) {
  collapsedGroups[group] = !collapsedGroups[group]
}

function isActive(name: string): boolean {
  return route.name === name
}

function isActiveByPath(path: string): boolean {
  return route.path === path
}
</script>
