import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { formatIraqLocalInput, isValidIraqLocal } from '../../utils/phone'
import { formatAuthPassword, isValidAuthPassword } from '../../utils/password'
import { login } from '../../api/auth'
import { formatAuthError } from './AuthShell'
import {
  CheckIcon,
  GlassAuthFrame,
  LockIcon,
  UserIcon,
  glassAlertClass,
  glassFieldClass,
  glassFieldInputClass,
  glassPrimaryBtn,
} from './GlassAuthFrame'

export default function GlassLogin({ onSuccess, onGoRegister }) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const phoneId = useId()
  const passwordId = useId()
  const rememberId = useId()

  const [phoneLocal, setPhoneLocal] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [shake, setShake] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)

    if (!isValidIraqLocal(phoneLocal)) {
      setError(t('auth.invalidPhone'))
      setShake(true)
      window.setTimeout(() => setShake(false), 450)
      return
    }
    if (!isValidAuthPassword(password)) {
      setError(t('auth.invalidPassword'))
      setShake(true)
      window.setTimeout(() => setShake(false), 450)
      return
    }

    setSubmitting(true)
    try {
      await login(phoneLocal, password)
      void remember
      onSuccess()
    } catch (err) {
      setError(formatAuthError(err, t('auth.invalidCredentials')))
      setShake(true)
      window.setTimeout(() => setShake(false), 450)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <GlassAuthFrame
      dir={isAr ? 'rtl' : 'ltr'}
      title={t('auth.userLogin')}
      shake={shake}
      footer={
        <>
          {t('auth.noAccount')}{' '}
          <button
            type="button"
            onClick={onGoRegister}
            className="font-bold text-violet-700 underline-offset-2 hover:underline"
          >
            {t('auth.registerLink')}
          </button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className={glassFieldClass}>
          <span className="shrink-0 text-violet-600">
            <UserIcon />
          </span>
          <input
            id={phoneId}
            type="tel"
            inputMode="numeric"
            autoComplete="tel-national"
            autoFocus
            value={phoneLocal}
            onChange={(e) => setPhoneLocal(formatIraqLocalInput(e.target.value))}
            required
            maxLength={11}
            placeholder={t('auth.usernamePlaceholder')}
            className={glassFieldInputClass}
          />
        </div>
        <p className="px-1 text-xs text-violet-400">{t('auth.phoneHint')}</p>

        <div className={glassFieldClass}>
          <span className="shrink-0 text-violet-600">
            <LockIcon />
          </span>
          <input
            id={passwordId}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(formatAuthPassword(e.target.value))}
            required
            maxLength={4}
            placeholder={t('auth.password')}
            className={glassFieldInputClass}
          />
        </div>
        <p className="px-1 text-xs text-violet-400">{t('auth.passwordHint')}</p>

        <div className="flex items-center justify-between gap-3 px-1 pt-1 text-sm text-violet-500">
          <label htmlFor={rememberId} className="inline-flex cursor-pointer items-center gap-2">
            <input
              id={rememberId}
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="sr-only"
            />
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full ${
                remember ? 'bg-violet-600 text-white' : 'border-2 border-violet-300 bg-white'
              }`}
            >
              {remember ? <CheckIcon /> : null}
            </span>
            <span>{t('auth.rememberMe')}</span>
          </label>
          <button
            type="button"
            className="text-violet-400 underline-offset-2 hover:text-violet-600 hover:underline"
            onClick={() => setError(t('auth.forgotPasswordHint'))}
          >
            {t('auth.forgotPassword')}
          </button>
        </div>

        {error ? (
          <div role="alert" className={glassAlertClass}>
            {error}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={submitting || phoneLocal.length !== 11 || password.length !== 4}
          className={`mt-2 ${glassPrimaryBtn} ${isAr ? '' : 'uppercase tracking-[0.18em]'}`}
        >
          {submitting ? t('auth.signingIn') : t('auth.loginCta')}
        </button>
      </form>
    </GlassAuthFrame>
  )
}
