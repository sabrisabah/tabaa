import { useTranslation } from 'react-i18next'

export default function LanguageSwitcher({ className = '', variant = 'light' }) {
  const { i18n, t } = useTranslation()
  const locale = i18n.language?.startsWith('ar') ? 'ar' : 'en'
  const glass = variant === 'glass'

  return (
    <div
      className={`inline-flex items-center gap-1 rounded-full border p-1 backdrop-blur ${
        glass
          ? 'border-white/35 bg-white/10 shadow-md shadow-violet-950/20'
          : 'border-slate-200 bg-white/90 shadow-sm'
      } ${className}`}
      role="group"
      aria-label={t('common.language')}
    >
      <button
        type="button"
        onClick={() => i18n.changeLanguage('en')}
        className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
          locale === 'en'
            ? glass
              ? 'bg-white text-slate-800'
              : 'bg-slate-900 text-white'
            : glass
              ? 'text-white/80 hover:bg-white/15'
              : 'text-slate-600 hover:bg-slate-50'
        }`}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => i18n.changeLanguage('ar')}
        className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
          locale === 'ar'
            ? glass
              ? 'bg-white text-slate-800'
              : 'bg-slate-900 text-white'
            : glass
              ? 'text-white/80 hover:bg-white/15'
              : 'text-slate-600 hover:bg-slate-50'
        }`}
      >
        ع
      </button>
    </div>
  )
}
