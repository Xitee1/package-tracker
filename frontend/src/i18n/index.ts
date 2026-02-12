import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import de from './locales/de.json'

function detectLocale(): string {
  const saved = localStorage.getItem('locale')
  if (saved && ['en', 'de'].includes(saved)) return saved
  const browserLang = navigator.language
  if (browserLang.startsWith('de')) return 'de'
  return 'en'
}

const locale = detectLocale()
document.documentElement.lang = locale

const i18n = createI18n({
  legacy: false,
  locale,
  fallbackLocale: 'en',
  messages: { en, de },
})

export default i18n
