<template>
  <div class="flex items-center justify-center gap-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
    <button
      @click="themeStore.setTheme('light')"
      class="p-1.5 rounded-md transition-colors"
      :class="
        themeStore.preference === 'light'
          ? 'bg-white dark:bg-gray-600 shadow-sm text-yellow-500'
          : 'text-gray-400 hover:text-gray-500 dark:hover:text-gray-300'
      "
      title="Light"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
        />
      </svg>
    </button>
    <button
      @click="themeStore.setTheme('system')"
      class="p-1.5 rounded-md transition-colors"
      :class="
        themeStore.preference === 'system'
          ? 'bg-white dark:bg-gray-600 shadow-sm text-blue-500'
          : 'text-gray-400 hover:text-gray-500 dark:hover:text-gray-300'
      "
      title="System"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
    </button>
    <button
      @click="themeStore.setTheme('dark')"
      class="p-1.5 rounded-md transition-colors"
      :class="
        themeStore.preference === 'dark'
          ? 'bg-white dark:bg-gray-600 shadow-sm text-indigo-400'
          : 'text-gray-400 hover:text-gray-500 dark:hover:text-gray-300'
      "
      title="Dark"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
        />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
</script>
