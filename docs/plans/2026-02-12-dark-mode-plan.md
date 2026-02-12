# Dark Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dark mode with system preference detection and manual override toggle to the Package Tracker frontend.

**Architecture:** Tailwind CSS 4 `dark:` variants on all components, controlled by a `.dark` class on `<html>`. A Pinia store manages preference (light/dark/system) in localStorage. An inline script in `index.html` applies the class before first paint to prevent flash.

**Tech Stack:** Tailwind CSS 4 (`@custom-variant`), Vue 3 Composition API, Pinia, localStorage

**Design doc:** `docs/plans/2026-02-12-dark-mode-design.md`

---

### Task 1: CSS and HTML Infrastructure

**Files:**
- Modify: `frontend/src/assets/main.css`
- Modify: `frontend/index.html`

**Step 1: Add custom dark variant to main.css**

Replace the contents of `frontend/src/assets/main.css` with:

```css
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));
```

This makes `dark:` utilities respond to a `.dark` class on any ancestor element, enabling manual toggle.

**Step 2: Add theme initialization script to index.html**

Replace `frontend/index.html` with:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Package Tracker</title>
    <script>
      (function() {
        var theme = localStorage.getItem('theme');
        var dark = theme === 'dark' || (theme !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
        if (dark) document.documentElement.classList.add('dark');
      })();
    </script>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

This runs before any rendering to prevent a flash of the wrong theme.

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css frontend/index.html
git commit -m "feat(dark-mode): add CSS custom variant and theme init script"
```

---

### Task 2: Theme Store

**Files:**
- Create: `frontend/src/stores/theme.ts`

**Step 1: Create the theme Pinia store**

Create `frontend/src/stores/theme.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'system'

export const useThemeStore = defineStore('theme', () => {
  const preference = ref<ThemePreference>(
    (localStorage.getItem('theme') as ThemePreference) || 'system',
  )

  let mediaQuery: MediaQueryList | null = null
  let mediaListener: ((e: MediaQueryListEvent) => void) | null = null

  function applyTheme() {
    const isDark =
      preference.value === 'dark' ||
      (preference.value === 'system' &&
        window.matchMedia('(prefers-color-scheme: dark)').matches)

    document.documentElement.classList.toggle('dark', isDark)
  }

  function cleanupListener() {
    if (mediaQuery && mediaListener) {
      mediaQuery.removeEventListener('change', mediaListener)
      mediaQuery = null
      mediaListener = null
    }
  }

  function setTheme(value: ThemePreference) {
    preference.value = value
    localStorage.setItem('theme', value)
    cleanupListener()

    if (value === 'system') {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaListener = () => applyTheme()
      mediaQuery.addEventListener('change', mediaListener)
    }

    applyTheme()
  }

  // Initialize: sync with the inline script's state and set up listener
  function init() {
    if (preference.value === 'system') {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaListener = () => applyTheme()
      mediaQuery.addEventListener('change', mediaListener)
    }
    applyTheme()
  }

  init()

  return { preference, setTheme }
})
```

**Step 2: Commit**

```bash
git add frontend/src/stores/theme.ts
git commit -m "feat(dark-mode): add theme Pinia store with system preference support"
```

---

### Task 3: ThemeToggle Component

**Files:**
- Create: `frontend/src/components/ThemeToggle.vue`

**Step 1: Create the ThemeToggle component**

Create `frontend/src/components/ThemeToggle.vue`:

```vue
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
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
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
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
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
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
</script>
```

**Step 2: Commit**

```bash
git add frontend/src/components/ThemeToggle.vue
git commit -m "feat(dark-mode): add ThemeToggle component"
```

---

### Task 4: AppLayout Dark Mode + ThemeToggle Integration

**Files:**
- Modify: `frontend/src/components/AppLayout.vue`

**Step 1: Add dark variants and mount ThemeToggle**

Replace the entire `<template>` and `<script>` of `frontend/src/components/AppLayout.vue` with:

```vue
<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <!-- Mobile sidebar backdrop -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-40 bg-black/50 lg:hidden"
      @click="sidebarOpen = false"
    ></div>

    <!-- Sidebar -->
    <aside
      class="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col transform transition-transform duration-200 ease-in-out"
      :class="sidebarOpen ? 'translate-x-0' : 'max-lg:-translate-x-full'"
    >
      <!-- Logo / Title -->
      <div class="flex items-center gap-3 px-5 py-5 border-b border-gray-200 dark:border-gray-700">
        <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
        <span class="text-lg font-bold text-gray-900 dark:text-white">Package Tracker</span>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors"
          :class="isActive(item.to) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'"
          @click="sidebarOpen = false"
        >
          <span v-html="item.icon" class="w-5 h-5 flex-shrink-0"></span>
          {{ item.label }}
        </router-link>

        <!-- Admin Section -->
        <template v-if="auth.isAdmin">
          <div class="pt-4 pb-1 px-3">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Admin</p>
          </div>
          <router-link
            v-for="item in adminNavItems"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors"
            :class="isActive(item.to) ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'"
            @click="sidebarOpen = false"
          >
            <span v-html="item.icon" class="w-5 h-5 flex-shrink-0"></span>
            {{ item.label }}
          </router-link>
        </template>
      </nav>

      <!-- Theme Toggle -->
      <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
        <ThemeToggle />
      </div>

      <!-- User Info -->
      <div class="border-t border-gray-200 dark:border-gray-700 p-4">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ auth.user?.username }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{{ auth.isAdmin ? 'Admin' : 'User' }}</p>
          </div>
          <button
            @click="handleLogout"
            class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Logout"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="lg:pl-64">
      <!-- Top bar (mobile) -->
      <div class="sticky top-0 z-30 flex items-center gap-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3 lg:hidden">
        <button
          @click="sidebarOpen = true"
          class="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <span class="text-lg font-bold text-gray-900 dark:text-white">Package Tracker</span>
      </div>

      <!-- Page Content -->
      <main>
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const sidebarOpen = ref(false)

const navItems = [
  {
    to: '/dashboard',
    label: 'Dashboard',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>',
  },
  {
    to: '/orders',
    label: 'Orders',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>',
  },
  {
    to: '/accounts',
    label: 'Email Accounts',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>',
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>',
  },
]

const adminNavItems = [
  {
    to: '/admin/users',
    label: 'Users',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>',
  },
  {
    to: '/admin/llm',
    label: 'LLM Config',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>',
  },
  {
    to: '/admin/system',
    label: 'System',
    icon: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>',
  },
]

function isActive(path: string): boolean {
  if (path === '/orders' && route.path.startsWith('/orders/')) return true
  return route.path === path
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
```

**Step 2: Verify the build compiles**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

**Step 3: Commit**

```bash
git add frontend/src/components/AppLayout.vue
git commit -m "feat(dark-mode): add dark variants to AppLayout and integrate ThemeToggle"
```

---

### Task 5: StatusBadge Dark Mode

**Files:**
- Modify: `frontend/src/components/StatusBadge.vue`

**Step 1: Add dark variants to status badge colors**

Replace the `statusConfig` object in `frontend/src/components/StatusBadge.vue:17-24` with:

```typescript
const statusConfig: Record<string, { class: string; label: string }> = {
  ordered: { class: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300', label: 'Ordered' },
  shipment_preparing: { class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300', label: 'Preparing' },
  shipped: { class: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300', label: 'Shipped' },
  in_transit: { class: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300', label: 'In Transit' },
  out_for_delivery: { class: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300', label: 'Out for Delivery' },
  delivered: { class: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300', label: 'Delivered' },
}
```

Also update the fallback in `badgeClass` on line 27:

```typescript
const badgeClass = computed(() => {
  return statusConfig[props.status]?.class || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
})
```

**Step 2: Commit**

```bash
git add frontend/src/components/StatusBadge.vue
git commit -m "feat(dark-mode): add dark variants to StatusBadge"
```

---

### Task 6: LoginView and SetupView Dark Mode

**Files:**
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/SetupView.vue`

These two views are almost identical in structure, so apply the same pattern.

**Step 1: Update LoginView.vue template**

Replace the `<template>` section of `frontend/src/views/LoginView.vue` with:

```html
<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-8">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Package Tracker</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Sign in to your account</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div v-if="error" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm">
            {{ error }}
          </div>

          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Username</label>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">Signing in...</span>
            <span v-else>Sign In</span>
          </button>
        </form>

        <div class="mt-6 text-center">
          <router-link to="/setup" class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300">
            First time? Create admin account
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
```

The `<script>` section stays unchanged.

**Step 2: Update SetupView.vue template**

Replace the `<template>` section of `frontend/src/views/SetupView.vue` with:

```html
<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
    <div class="w-full max-w-md">
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-md p-8">
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Package Tracker</h1>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Create Admin Account</p>
        </div>

        <form @submit.prevent="handleSetup" class="space-y-5">
          <div v-if="error" class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-md text-sm">
            {{ error }}
          </div>

          <div v-if="success" class="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 px-4 py-3 rounded-md text-sm">
            {{ success }}
          </div>

          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Username</label>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Choose a username"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Choose a password"
            />
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Confirm Password</label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Confirm your password"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading">Creating account...</span>
            <span v-else>Create Admin Account</span>
          </button>
        </form>

        <div class="mt-6 text-center">
          <router-link to="/login" class="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300">
            Already have an account? Sign in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
```

The `<script>` section stays unchanged.

**Step 3: Commit**

```bash
git add frontend/src/views/LoginView.vue frontend/src/views/SetupView.vue
git commit -m "feat(dark-mode): add dark variants to LoginView and SetupView"
```

---

### Task 7: DashboardView Dark Mode

**Files:**
- Modify: `frontend/src/views/DashboardView.vue`

**Step 1: Add dark variants to the DashboardView template**

Apply these changes to `frontend/src/views/DashboardView.vue`:

- Line 3: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 7 (status cards): `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 10: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 13: `bg-blue-100` → `bg-blue-100 dark:bg-blue-900/40`
- Same pattern for the other 3 status cards (indigo, orange, green icon backgrounds)
- Line 21, 35, 49: same card pattern for the other 3 status cards
- Line 65 (Recent Orders card): `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 66: `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 67: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 68: `text-blue-600 hover:text-blue-500` → `text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300`
- Line 73, 77: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 84: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 92: `divide-gray-200` → `divide-gray-200 dark:divide-gray-700`
- Line 97: `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-800`
- Line 100: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 103: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 107: `text-gray-600` → `text-gray-600 dark:text-gray-400`
- Line 118: `text-gray-600` → `text-gray-600 dark:text-gray-400`
- Line 121: `text-gray-600` → `text-gray-600 dark:text-gray-400`

Also update the `statusClass` function in the script (line 156-164):

```typescript
function statusClass(status: string): string {
  const classes: Record<string, string> = {
    ordered: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    shipment_preparing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
    shipped: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
    in_transit: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    out_for_delivery: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
    delivered: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  }
  return classes[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/DashboardView.vue
git commit -m "feat(dark-mode): add dark variants to DashboardView"
```

---

### Task 8: OrdersView Dark Mode

**Files:**
- Modify: `frontend/src/views/OrdersView.vue`

**Step 1: Add dark variants to the OrdersView template**

Apply these class changes throughout `frontend/src/views/OrdersView.vue`:

- Line 4: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 8: `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 14: `text-gray-400` → `text-gray-400 dark:text-gray-500`
- Line 21: input — add `bg-white dark:bg-gray-800 text-gray-900 dark:text-white`, change `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 30: `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 39: active tab `border-blue-500 text-blue-600` stays, add inactive `dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500`
- Line 49: active badge `bg-blue-100 text-blue-600` → add `dark:bg-blue-900/40 dark:text-blue-400`, inactive `bg-gray-100 text-gray-600` → add `dark:bg-gray-700 dark:text-gray-400`
- Line 61: `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 62, 66: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 74: `text-gray-500` → `text-gray-500 dark:text-gray-400`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 83: `divide-gray-200` → `divide-gray-200 dark:divide-gray-700`
- Line 88: `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-800`
- Line 91: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 94: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 98, 101, 107, 110: `text-gray-600` → `text-gray-600 dark:text-gray-400`

**Step 2: Commit**

```bash
git add frontend/src/views/OrdersView.vue
git commit -m "feat(dark-mode): add dark variants to OrdersView"
```

---

### Task 9: OrderDetailView Dark Mode

**Files:**
- Modify: `frontend/src/views/OrderDetailView.vue`

**Step 1: Add dark variants to OrderDetailView template**

Apply these class changes throughout `frontend/src/views/OrderDetailView.vue`:

- Line 5: `text-blue-600 hover:text-blue-500` → add `dark:text-blue-400 dark:hover:text-blue-300`
- Line 14: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 19: error box — `bg-red-50` → `bg-red-50 dark:bg-red-900/30`, `border-red-200` → `border-red-200 dark:border-red-800`, `text-red-700` → `text-red-700 dark:text-red-400`
- Line 28: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 31: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 39: edit button — `text-gray-700` → `text-gray-700 dark:text-gray-300`, `bg-white` → `bg-white dark:bg-gray-800`, `border-gray-300` → `border-gray-300 dark:border-gray-600`, `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-700`
- Line 44: delete button — `text-red-700` → `text-red-700 dark:text-red-400`, `bg-white` → `bg-white dark:bg-gray-800`, `border-red-300` → `border-red-300 dark:border-red-700`, `hover:bg-red-50` → `hover:bg-red-50 dark:hover:bg-red-900/30`
- Line 60, 114: cards — `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 61, 115: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 66, 94: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 67, 82-86, 121, 129: inputs — add `bg-white dark:bg-gray-800 text-gray-900 dark:text-white`, change `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 71: select — same input dark variants
- Line 95: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 134-146: save/cancel buttons — same button dark variants as edit button
- Line 154: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 170-197: items table — same table dark patterns (borders, text, hover, divide)
- Line 197-234: timeline — `bg-gray-200` line → `bg-gray-200 dark:bg-gray-700`, dot colors adjusted, text colors adjusted
- Line 208: timeline line — `bg-gray-200` → `bg-gray-200 dark:bg-gray-700`
- Line 213: active dot bg — `bg-blue-100` → `bg-blue-100 dark:bg-blue-900/40`, inactive `bg-gray-100` → `bg-gray-100 dark:bg-gray-800`
- Line 221, 224, 227: `text-gray-900` / `text-gray-600` / `text-gray-400` → add dark variants
- Line 240: modal — `bg-white` → `bg-white dark:bg-gray-900`
- Line 241, 243: modal text — add dark variants
- Line 248, 252: modal buttons — add dark variants

**Step 2: Commit**

```bash
git add frontend/src/views/OrderDetailView.vue
git commit -m "feat(dark-mode): add dark variants to OrderDetailView"
```

---

### Task 10: AccountsView Dark Mode

**Files:**
- Modify: `frontend/src/views/AccountsView.vue`

**Step 1: Add dark variants to AccountsView template**

Apply these class changes throughout `frontend/src/views/AccountsView.vue`:

- Line 4: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 18: form card — `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 19: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 23: error box — add dark variants (`dark:bg-red-900/30 dark:border-red-800 dark:text-red-400`)
- Line 30, 41, 51, 64, 75, 90: labels — `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 33-36, 43-46, etc.: inputs — add `bg-white dark:bg-gray-800 text-gray-900 dark:text-white`, `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 106: checkbox — `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 108: `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 122: cancel button — add dark variants
- Line 131: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 138: empty state card — add dark variants
- Line 148: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 168: account cards — add dark variants
- Line 175: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 178: active badge — `bg-green-100 text-green-800` → add `dark:bg-green-900/40 dark:text-green-400`, inactive `bg-gray-100 text-gray-600` → add `dark:bg-gray-700 dark:text-gray-400`
- Line 183: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 185, 191, 197: `text-gray-400` → `text-gray-400 dark:text-gray-500`
- Line 209, 216: secondary/edit buttons — add dark variants
- Line 221: delete button — add dark red variants
- Line 229: expand button — `text-gray-400 hover:text-gray-600` → add `dark:hover:text-gray-300`, `hover:bg-gray-100` → add `dark:hover:bg-gray-800`
- Line 249: test result — add dark variants for green/red
- Line 256: expanded section — `border-gray-200 bg-gray-50` → `border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50`
- Line 258: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 262: load folders button — add dark variants
- Line 271: folder error — add dark variants
- Line 278: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 286, 317: folder items — `bg-white` → `bg-white dark:bg-gray-800`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 288: `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 347-370: delete modal — same dark modal pattern as OrderDetailView

**Step 2: Commit**

```bash
git add frontend/src/views/AccountsView.vue
git commit -m "feat(dark-mode): add dark variants to AccountsView"
```

---

### Task 11: SettingsView Dark Mode

**Files:**
- Modify: `frontend/src/views/SettingsView.vue`

**Step 1: Add dark variants to SettingsView template**

Apply these class changes to `frontend/src/views/SettingsView.vue`:

- Line 3: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 6: card — `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 7: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 9: success box — add `dark:bg-green-900/30 dark:border-green-800 dark:text-green-400`
- Line 13: error box — add `dark:bg-red-900/30 dark:border-red-800 dark:text-red-400`
- Line 19, 30, 41: labels — `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 24, 35, 46: inputs — add `bg-white dark:bg-gray-800 text-gray-900 dark:text-white`, `border-gray-300` → `border-gray-300 dark:border-gray-600`

**Step 2: Commit**

```bash
git add frontend/src/views/SettingsView.vue
git commit -m "feat(dark-mode): add dark variants to SettingsView"
```

---

### Task 12: Admin Views Dark Mode

**Files:**
- Modify: `frontend/src/views/admin/UsersView.vue`
- Modify: `frontend/src/views/admin/LLMConfigView.vue`
- Modify: `frontend/src/views/admin/SystemView.vue`

**Step 1: Add dark variants to UsersView.vue**

Apply the standard dark patterns to `frontend/src/views/admin/UsersView.vue`:

- Line 4: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 18: form card — `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 19: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 21: error — add dark red variants
- Line 28, 39: labels — `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 33, 44: inputs — add dark input variants
- Line 56: checkbox label — `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 57: checkbox — `border-gray-300` → `border-gray-300 dark:border-gray-600`
- Line 72: cancel button — add dark variants
- Line 81: users table card — add dark card variants
- Line 82: loading — `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 85: error — add dark error variants
- Line 91: thead — `text-gray-500` → `text-gray-500 dark:text-gray-400`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 98: tbody — `divide-gray-200` → `divide-gray-200 dark:divide-gray-700`
- Line 99: `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-800`
- Line 100: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 103: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 106: "You" badge — `bg-blue-50 text-blue-700` → add `dark:bg-blue-900/30 dark:text-blue-400`
- Line 115: admin badge — `bg-purple-100 text-purple-800` → add `dark:bg-purple-900/40 dark:text-purple-300`, user badge `bg-gray-100 text-gray-700` → add `dark:bg-gray-700 dark:text-gray-300`
- Line 126-130: toggle admin button — add dark variants
- Line 137: delete button — add dark red variants
- Line 150-173: delete modal — add dark modal variants

**Step 2: Add dark variants to LLMConfigView.vue**

Apply the standard dark patterns to `frontend/src/views/admin/LLMConfigView.vue`:

- Line 3: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 5: card — add dark card variants
- Line 6: error — add dark error variants
- Line 10: loading — `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 13: success — add dark green variants
- Line 17: save error — add dark red variants
- Line 23: label — `text-gray-700` → `text-gray-700 dark:text-gray-300`
- Line 28: select — add dark input variants
- Line 40: custom input — add dark input variants
- Line 44: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 52: model name label + input — add dark variants
- Line 63-65: API key label spans — `text-gray-700` → `text-gray-700 dark:text-gray-300`, `text-gray-400` stays
- Line 70: API key input — add dark input variants
- Line 79-80: base URL label — add dark label variants
- Line 86: base URL input — add dark input variants
- Line 104: test connection button — `text-gray-700` → `text-gray-700 dark:text-gray-300`, `bg-white` → `bg-white dark:bg-gray-800`, `border-gray-300` → `border-gray-300 dark:border-gray-600`, `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-700`
- Line 115: test result — add dark variants for both success and error states

**Step 3: Add dark variants to SystemView.vue**

Apply the standard dark patterns to `frontend/src/views/admin/SystemView.vue`:

- Line 4: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 8: refresh button — `text-gray-700` → `text-gray-700 dark:text-gray-300`, `bg-white` → `bg-white dark:bg-gray-800`, `border-gray-300` → `border-gray-300 dark:border-gray-600`, `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-700`
- Line 23: error — add dark error variants
- Line 27: loading — `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 32, 36, 40: overview cards — `bg-white` → `bg-white dark:bg-gray-900`, `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 33, 37: `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 34: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 49: workers table — add dark card variants
- Line 50: `border-gray-200` → `border-gray-200 dark:border-gray-700`
- Line 51: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 54: empty state — `text-gray-500` → `text-gray-500 dark:text-gray-400`
- Line 61: thead — add dark header variants
- Line 67: tbody — `divide-gray-200` → `divide-gray-200 dark:divide-gray-700`
- Line 68: `hover:bg-gray-50` → `hover:bg-gray-50 dark:hover:bg-gray-800`
- Line 69: `text-gray-900` → `text-gray-900 dark:text-white`
- Line 73: running badge — `bg-green-100 text-green-800` → add `dark:bg-green-900/40 dark:text-green-400`, stopped `bg-gray-100 text-gray-600` → add `dark:bg-gray-700 dark:text-gray-400`
- Line 76: running dot — `bg-green-500` / `bg-gray-400` stay (visible in both themes)
- Line 83: error text — `text-gray-400` / `text-red-600` → add `dark:text-gray-500` / keep `dark:text-red-400`

**Step 4: Commit**

```bash
git add frontend/src/views/admin/UsersView.vue frontend/src/views/admin/LLMConfigView.vue frontend/src/views/admin/SystemView.vue
git commit -m "feat(dark-mode): add dark variants to admin views"
```

---

### Task 13: Final Build Verification

**Files:** None (verification only)

**Step 1: Run the full frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript or compilation errors.

**Step 2: Run type checking**

Run: `cd frontend && npm run type-check`
Expected: No type errors.

**Step 3: Run linting**

Run: `cd frontend && npm run lint`
Expected: No lint errors (or only auto-fixable ones).

**Step 4: Update the design doc files list**

Update `docs/plans/2026-02-12-dark-mode-design.md` to fix the file paths for admin views:
- `frontend/src/views/AdminUsersView.vue` → `frontend/src/views/admin/UsersView.vue`
- `frontend/src/views/AdminLLMConfigView.vue` → `frontend/src/views/admin/LLMConfigView.vue`
- Add `frontend/src/views/admin/SystemView.vue` (was missing from design)
- Remove `HomeView.vue` from the list (trivial, no color classes)

**Step 5: Commit**

```bash
git add docs/plans/2026-02-12-dark-mode-design.md
git commit -m "docs: fix file paths in dark mode design doc"
```
