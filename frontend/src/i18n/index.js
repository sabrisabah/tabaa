import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import ar from './locales/ar.json'

const STORAGE_KEY = 'app_locale'

export function getStoredLocale() {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'ar' || saved === 'en' ? saved : 'en'
}

export function applyDocumentDirection(locale) {
  const dir = locale === 'ar' ? 'rtl' : 'ltr'
  document.documentElement.lang = locale
  document.documentElement.dir = dir
}

const initialLocale = getStoredLocale()
applyDocumentDirection(initialLocale)

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
  },
  lng: initialLocale,
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
})

i18n.on('languageChanged', (locale) => {
  localStorage.setItem(STORAGE_KEY, locale)
  applyDocumentDirection(locale)
})

export default i18n
