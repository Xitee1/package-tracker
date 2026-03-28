<template>
  <div>
    <div class="relative">
      <button
        @click="isOpen = !isOpen"
        @keydown.esc.window="isOpen = false"
        :aria-expanded="isOpen"
        aria-haspopup="true"
        class="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white"
      >
        <span>{{ label }}</span>
        <svg
          class="w-4 h-4 transition-transform duration-200"
          :class="{ 'rotate-180': isOpen }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        v-if="isOpen"
        class="absolute z-20 left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 max-h-64 overflow-y-auto"
      >
        <slot />
      </div>
    </div>
    <div v-if="isOpen" class="fixed inset-0 z-10" @click="isOpen = false"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

defineProps<{
  label: string
}>()

const route = useRoute()
const isOpen = ref(false)

watch(() => route.path, () => {
  isOpen.value = false
})
</script>
