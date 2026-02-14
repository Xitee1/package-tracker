<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('settings.title') }}
    </h1>

    <div class="flex flex-col sm:flex-row gap-6">
      <!-- Vertical Tab Nav with Collapsible Groups -->
      <nav class="sm:w-52 flex-shrink-0">
        <div class="flex sm:flex-col gap-1">
          <!-- Queue (core, always visible) -->
          <router-link
            to="/admin/settings/queue"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="isActive('/admin/settings/queue')
              ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
          >
            {{ $t('settings.queue') }}
          </router-link>

          <!-- Module Groups -->
          <template v-for="group in sidebarGroups" :key="group.group">
            <button
              @click="toggleGroup(group.group)"
              class="flex items-center justify-between w-full px-3 py-2 mt-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300"
            >
              {{ group.group }}
              <svg
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': !collapsedGroups[group.group] }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <template v-if="!collapsedGroups[group.group]">
              <router-link
                v-for="item in group.items"
                :key="item.to"
                :to="item.to"
                class="px-3 py-2 pl-5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap block"
                :class="isActive(item.to)
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
              >
                {{ item.label }}
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
import { reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getAdminSidebarItems } from '@/core/moduleRegistry'

const { t } = useI18n()
const route = useRoute()

const sidebarGroups = getAdminSidebarItems()

const collapsedGroups = reactive<Record<string, boolean>>({})

function toggleGroup(group: string) {
  collapsedGroups[group] = !collapsedGroups[group]
}

function isActive(path: string): boolean {
  return route.path === path
}
</script>
