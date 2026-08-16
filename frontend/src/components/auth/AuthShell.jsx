import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../LanguageSwitcher'

export function EyeIcon({ open }) {
  if (open) {
    return (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
        <path
          d="M3 12s3.5-7 9-7 9 7 9 7-3.5 7-9 7-9-7-9-7Z"
          stroke="currentColor"
          strokeWidth="1.75"
        />
        <circle cx="12" cy="12" r="2.75" stroke="currentColor" strokeWidth="1.75" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
      <path
        d="M3 12s3.5-7 9-7 9 7 9 7-3.5 7-9 7-9-7-9-7Z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  )
}

function ClinicMark({ large = false }) {
  const size = large ? 'h-16 w-16' : 'h-12 w-12'
  const icon = large ? 'h-8 w-8' : 'h-6 w-6'
  return (
    <div
      className={`flex ${size} items-center justify-center rounded-2xl bg-gradient-to-br from-teal-600 to-emerald-800 text-white shadow-lg shadow-teal-900/30`}
    >
      <svg viewBox="0 0 24 24" className={icon} fill="none" aria-hidden="true">
        <path
          d="M12 3c3.2 2.4 5.5 5.6 5.5 9.2 0 4.1-2.6 7.4-5.5 8.8-2.9-1.4-5.5-4.7-5.5-8.8C6.5 8.6 8.8 5.4 12 3Z"
          fill="currentColor"
          opacity="0.9"
        />
        <path d="M12 8v8M8 12h8" stroke="#ecfdf5" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </div>
  )
}

export const authInputClass =
  'w-full rounded-2xl border border-teal-900/10 bg-white px-4 py-3.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-4 focus:ring-teal-600/15'

export function formatAuthError(err, fallback) {
  const data = err.response?.data
  if (!data) return fallback
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data)) return data.join(' ')
  if (typeof data === 'object') {
    return Object.entries(data)
      .map(([key, value]) => {
        const message = Array.isArray(value) ? value.join(' ') : String(value)
        return key === 'detail' ? message : `${key}: ${message}`
      })
      .join(' ')
  }
  return fallback
}

export function AuthShell({
  title,
  subtitle,
  asideTitle,
  asideBody,
  footer,
  shake = false,
  wide = false,
  children,
}) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')

  return (
    <div
      className="relative flex min-h-screen overflow-hidden font-[family-name:var(--font-clinic)]"
      dir={isAr ? 'rtl' : 'ltr'}
      style={{
        background:
          'linear-gradient(145deg, #0f3d3a 0%, #134e4a 28%, #ecfdf5 28%, #f0fdfa 62%, #fff7ed 100%)',
      }}
    >
      <div className="absolute end-4 top-4 z-20 sm:end-6 sm:top-6">
        <LanguageSwitcher />
      </div>

      <div
        className="pointer-events-none absolute inset-0 z-0 opacity-40"
        style={{
          backgroundImage:
            'radial-gradient(circle at 12% 18%, rgba(45,212,191,0.35), transparent 34%), radial-gradient(circle at 88% 12%, rgba(251,146,60,0.18), transparent 30%), radial-gradient(circle at 70% 85%, rgba(15,118,110,0.12), transparent 36%)',
        }}
      />

      <aside className="relative z-10 hidden w-[46%] shrink-0 flex-col justify-between overflow-hidden px-10 py-12 text-teal-50 lg:flex">
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(circle at 30% 20%, rgba(45,212,191,0.28), transparent 42%), linear-gradient(180deg, rgba(15,61,58,0.2), rgba(15,61,58,0.75))',
          }}
        />
        <div
          className="pointer-events-none absolute -bottom-24 -start-16 h-72 w-72 rounded-full border border-teal-200/10"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute bottom-20 start-24 h-40 w-40 rounded-full border border-teal-200/10"
          aria-hidden
        />

        <div className="relative">
          <div className="flex items-center gap-4">
            <ClinicMark large />
            <div>
              <p className="font-[family-name:var(--font-display)] text-4xl font-bold tracking-tight text-white">
                {t('common.appName')}
              </p>
              <p className="mt-1 text-sm text-teal-100/80">{t('common.tagline')}</p>
            </div>
          </div>
        </div>

        <div className="relative space-y-5">
          <h2 className="max-w-md font-[family-name:var(--font-display)] text-4xl font-semibold leading-tight tracking-tight text-white">
            {asideTitle}
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-teal-50/75">{asideBody}</p>
        </div>

        <p className="relative text-xs text-teal-100/50">{t('auth.createAccountFooter')}</p>
      </aside>

      <main className="relative z-10 flex min-w-0 flex-1 items-center justify-center px-4 py-10 sm:px-8">
        <div
          className={`w-full transition-transform duration-300 ${
            wide ? 'max-w-xl' : 'max-w-md'
          } ${shake ? 'animate-[login-shake_0.45s_ease-in-out]' : ''}`}
        >
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <ClinicMark />
            <div>
              <p className="font-[family-name:var(--font-display)] text-2xl font-bold text-teal-950">
                {t('common.appName')}
              </p>
              <p className="text-xs text-teal-800/70">{t('common.tagline')}</p>
            </div>
          </div>

          <div className="rounded-[1.75rem] border border-white/70 bg-white/95 p-6 shadow-[0_30px_80px_-40px_rgba(15,61,58,0.55)] backdrop-blur-md sm:p-8">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-700/70">
                {t('common.appName')}
              </p>
              <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold tracking-tight text-teal-950 sm:text-[2rem]">
                {title}
              </h1>
              <p className="text-sm leading-relaxed text-slate-500">{subtitle}</p>
            </div>
            {children}
          </div>

          {footer ? <div className="mt-5 text-center text-sm text-teal-950/60">{footer}</div> : null}
        </div>
      </main>

      <style>{`
        @keyframes login-shake {
          0%, 100% { transform: translateX(0); }
          20% { transform: translateX(-6px); }
          40% { transform: translateX(6px); }
          60% { transform: translateX(-4px); }
          80% { transform: translateX(4px); }
        }
      `}</style>
    </div>
  )
}

export function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete = 'current-password',
  placeholder = '••••••••',
}) {
  const { t } = useTranslation()
  const generatedId = useId()
  const fieldId = id ?? generatedId
  const [showPassword, setShowPassword] = useState(false)

  return (
    <div className="space-y-2">
      <label htmlFor={fieldId} className="block text-sm font-medium text-teal-950/80">
        {label}
      </label>
      <div className="relative">
        <input
          id={fieldId}
          type={showPassword ? 'text' : 'password'}
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          required
          placeholder={placeholder}
          className={`${authInputClass} pe-12`}
        />
        <button
          type="button"
          onClick={() => setShowPassword((prev) => !prev)}
          className="absolute inset-y-0 end-0 flex items-center px-3 text-slate-400 transition hover:text-teal-800"
          aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
        >
          <EyeIcon open={showPassword} />
        </button>
      </div>
    </div>
  )
}
