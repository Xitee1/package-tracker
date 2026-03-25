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
      (preference.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

    document.documentElement.classList.toggle('dark', isDark)
    document.documentElement.style.colorScheme = isDark ? 'dark' : 'light'

    // Signal browser extensions (e.g. Dark Reader) to not apply their own dark theme
    let lock = document.head.querySelector('meta[name="darkreader-lock"]')
    if (isDark && !lock) {
      lock = document.createElement('meta')
      lock.setAttribute('name', 'darkreader-lock')
      document.head.appendChild(lock)
    } else if (!isDark && lock) {
      lock.remove()
    }
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
  if (preference.value === 'system') {
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaListener = () => applyTheme()
    mediaQuery.addEventListener('change', mediaListener)
  }
  applyTheme()

  return { preference, setTheme }
})
