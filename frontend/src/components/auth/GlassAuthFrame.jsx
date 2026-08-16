import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../LanguageSwitcher'

export const glassFieldClass =
  'flex h-12 w-full items-center gap-3 rounded-full bg-[#ece6f5] px-5 text-violet-700 transition focus-within:ring-2 focus-within:ring-violet-400/35'

export const glassFieldInputClass =
  'min-w-0 flex-1 bg-transparent text-sm text-slate-700 outline-none placeholder:text-violet-400/80'

export const glassPrimaryBtn =
  'flex h-12 w-full items-center justify-center rounded-full bg-gradient-to-r from-violet-600 via-fuchsia-500 to-rose-400 text-sm font-bold text-white shadow-lg shadow-fuchsia-400/30 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60'

export const glassGhostBtn =
  'flex h-12 items-center justify-center rounded-full border border-violet-200 bg-violet-50 px-5 text-sm font-semibold text-violet-800 transition hover:bg-violet-100'

export const glassAlertClass =
  'rounded-2xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-center text-sm text-rose-700'

const AUTH_GRADIENT =
  'linear-gradient(118deg, #4c1d95 0%, #6d28d9 28%, #c026d3 62%, #fb7185 82%, #fb923c 100%)'

function CapsuleDecor() {
  const pills = [
    { width: 280, height: 38, left: '-6%', bottom: '6%', rotate: -34, opacity: 0.95 },
    { width: 220, height: 32, left: '10%', bottom: '16%', rotate: -34, opacity: 0.8 },
    { width: 320, height: 42, left: '-10%', bottom: '26%', rotate: -34, opacity: 0.55 },
    { width: 170, height: 28, left: '28%', bottom: '8%', rotate: -34, opacity: 0.88 },
    { width: 250, height: 30, left: '16%', bottom: '36%', rotate: -34, opacity: 0.42 },
    { width: 140, height: 24, left: '38%', bottom: '22%', rotate: -34, opacity: 0.5 },
  ]

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute -left-16 top-10 h-72 w-72 rounded-full bg-white/15 blur-3xl" />
      <div className="absolute right-8 top-1/4 h-56 w-56 rounded-full bg-fuchsia-200/25 blur-3xl" />
      <div className="absolute bottom-24 right-1/4 h-40 w-40 rounded-full bg-orange-300/20 blur-2xl" />
      {pills.map((pill, index) => (
        <div
          key={index}
          className="absolute rounded-full"
          style={{
            width: pill.width,
            height: pill.height,
            left: pill.left,
            bottom: pill.bottom,
            opacity: pill.opacity,
            transform: `rotate(${pill.rotate}deg)`,
            background: 'linear-gradient(90deg, #fb923c 0%, #fb7185 45%, #f0abfc 100%)',
            boxShadow: '0 10px 28px rgba(251, 146, 60, 0.28)',
          }}
        />
      ))}
    </div>
  )
}

export function GlassAuthFrame({
  title,
  subtitle,
  footer,
  shake = false,
  wide = false,
  children,
  dir = 'ltr',
}) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const copyDir = isAr ? 'rtl' : 'ltr'

  return (
    <div className="flex min-h-screen overflow-x-hidden font-sans" dir="ltr">
      <aside
        className="relative hidden min-h-screen w-[58%] overflow-hidden text-white lg:flex lg:flex-col lg:items-center lg:justify-center"
        style={{ background: AUTH_GRADIENT }}
      >
        <CapsuleDecor />
        <div className="relative z-10 max-w-xl px-12 text-center xl:px-16" dir={copyDir}>
          <p className="text-sm font-semibold tracking-[0.28em] text-white/80">
            {t('common.tagline')}
          </p>
          <h2 className="mt-4 text-6xl font-bold leading-[1.15] tracking-tight drop-shadow-sm xl:text-7xl">
            {t('auth.welcomeHeading')}
          </h2>
          <p className="mx-auto mt-6 max-w-md text-lg font-medium leading-relaxed text-white/90 xl:text-xl">
            {t('auth.motivational')}
          </p>
        </div>
      </aside>

      <main className="relative flex min-h-screen min-w-0 flex-1 flex-col bg-white">
        <div
          className="relative overflow-hidden px-6 py-8 text-white lg:hidden"
          style={{ background: AUTH_GRADIENT }}
        >
          <CapsuleDecor />
          <div className="absolute end-4 top-4 z-20">
            <LanguageSwitcher variant="glass" />
          </div>
          <div className="relative z-10 pr-28 text-center" dir={copyDir}>
            <p className="text-xs font-semibold tracking-[0.22em] text-white/80">{t('common.tagline')}</p>
            <h2 className="mt-2 text-3xl font-bold leading-tight">{t('auth.welcomeHeading')}</h2>
            <p className="mt-2 text-sm text-white/85">{t('auth.motivational')}</p>
          </div>
        </div>

        <div className="absolute end-6 top-6 z-20 hidden lg:block">
          <LanguageSwitcher />
        </div>

        <div className="flex flex-1 items-center justify-center px-5 py-10 sm:px-10">
          <div
            dir={dir}
            className={`w-full transition-transform duration-300 ${
              wide ? 'max-w-xl' : 'max-w-[380px]'
            } ${shake ? 'animate-[login-shake_0.45s_ease-in-out]' : ''}`}
          >
            <div className="mb-8 text-center">
              <h1
                className={`text-2xl font-bold text-violet-800 ${
                  dir === 'ltr' ? 'uppercase tracking-[0.14em]' : ''
                }`}
              >
                {title}
              </h1>
              {subtitle ? <p className="mt-2 text-sm text-slate-500">{subtitle}</p> : null}
            </div>

            {children}

            {footer ? <div className="mt-8 text-center text-sm text-slate-500">{footer}</div> : null}
          </div>
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

export function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
      <circle cx="12" cy="8" r="3.25" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M5.5 19.5c1.4-3.2 3.7-4.7 6.5-4.7s5.1 1.5 6.5 4.7"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
      <rect x="6" y="10" width="12" height="10" rx="2" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M8.5 10V8a3.5 3.5 0 0 1 7 0v2"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" aria-hidden="true">
      <path
        d="M3.5 8.2 6.4 11l6.1-6.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
