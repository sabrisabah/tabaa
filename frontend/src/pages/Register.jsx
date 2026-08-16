import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { register } from '../api/auth'
import { previewTdee } from '../api/profile'
import { formatAuthError } from '../components/auth/AuthShell'
import {
  GlassAuthFrame,
  LockIcon,
  UserIcon,
  glassAlertClass,
  glassFieldClass,
  glassFieldInputClass,
  glassGhostBtn,
  glassPrimaryBtn,
} from '../components/auth/GlassAuthFrame'
import ProfileDetailsFields, {
  defaultProfileDetails,
  isProfileDetailsValid,
  profileDetailsToPayload,
} from '../components/auth/ProfileDetailsFields'
import TdeeResultsCard from '../components/auth/TdeeResultsCard'
import { formatIraqLocalInput, isValidIraqLocal } from '../utils/phone'

export default function Register({ onSuccess, onGoLogin }) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const [step, setStep] = useState(1)
  const [phoneLocal, setPhoneLocal] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [profile, setProfile] = useState(defaultProfileDetails)
  const [tdee, setTdee] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [calculating, setCalculating] = useState(false)
  const [shake, setShake] = useState(false)

  const canSubmitProfile = useMemo(() => isProfileDetailsValid(profile), [profile])

  function triggerShake(message) {
    setError(message)
    setShake(true)
    window.setTimeout(() => setShake(false), 450)
  }

  function handleContinueAccount(event) {
    event.preventDefault()
    setError(null)

    const local = phoneLocal
    if (!isValidIraqLocal(local)) {
      triggerShake(t('auth.invalidPhone'))
      return
    }
    if (!/^\d{4}$/.test(password)) {
      triggerShake(t('auth.passwordHint'))
      return
    }
    if (password !== passwordConfirm) {
      triggerShake(t('auth.passwordsMismatch'))
      return
    }
    setStep(2)
  }

  async function handleContinueProfile(event) {
    event.preventDefault()
    setError(null)

    if (!canSubmitProfile) {
      triggerShake(t('auth.completeProfile'))
      return
    }

    setCalculating(true)
    try {
      const payload = profileDetailsToPayload(profile)
      const result = await previewTdee(payload)
      setTdee(result)
      setStep(3)
    } catch (err) {
      triggerShake(formatAuthError(err, t('auth.couldNotCalculate')))
    } finally {
      setCalculating(false)
    }
  }

  async function handleCreateAccount(event) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await register({
        phone: phoneLocal,
        password,
        password_confirm: passwordConfirm,
        ...profileDetailsToPayload(profile),
      })
      onSuccess()
    } catch (err) {
      triggerShake(formatAuthError(err, t('auth.couldNotCreate')))
    } finally {
      setSubmitting(false)
    }
  }

  const titles = {
    1: { title: t('auth.userRegister'), subtitle: t('auth.step1Subtitle') },
    2: { title: t('auth.step2Title'), subtitle: t('auth.step2Subtitle') },
    3: { title: t('auth.step3Title'), subtitle: t('auth.step3Subtitle') },
  }

  return (
    <GlassAuthFrame
      dir={isAr ? 'rtl' : 'ltr'}
      title={titles[step].title}
      subtitle={titles[step].subtitle}
      asideTitle={t('auth.welcomeHeading')}
      asideBody={t('auth.welcomeRegisterBody')}
      shake={shake}
      wide={step !== 1}
      footer={
        <>
          {t('auth.haveAccount')}{' '}
          <button
            type="button"
            onClick={onGoLogin}
            className="font-bold text-violet-700 underline-offset-2 hover:underline"
          >
            {t('auth.loginTitle')}
          </button>
        </>
      }
    >
      {step === 1 ? (
        <form onSubmit={handleContinueAccount} className="space-y-4" noValidate>
          <div className={glassFieldClass}>
            <span className="shrink-0 text-violet-600">
              <UserIcon />
            </span>
            <input
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

          <div className={glassFieldClass}>
            <span className="shrink-0 text-violet-600">
              <LockIcon />
            </span>
            <input
              type="password"
              inputMode="numeric"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value.replace(/\D/g, '').slice(0, 4))}
              required
              maxLength={4}
              placeholder={t('auth.password')}
              className={glassFieldInputClass}
            />
          </div>

          <div className={glassFieldClass}>
            <span className="shrink-0 text-violet-600">
              <LockIcon />
            </span>
            <input
              type="password"
              inputMode="numeric"
              autoComplete="new-password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value.replace(/\D/g, '').slice(0, 4))}
              required
              maxLength={4}
              placeholder={t('auth.confirmPassword')}
              className={glassFieldInputClass}
            />
          </div>

          <p className="px-1 text-xs text-violet-400">{t('auth.passwordHint')}</p>

          {error ? (
            <div role="alert" className={glassAlertClass}>
              {error}
            </div>
          ) : null}

          <button type="submit" className={glassPrimaryBtn}>
            {t('common.continue')}
          </button>
        </form>
      ) : null}

      {step === 2 ? (
        <form onSubmit={handleContinueProfile} className="space-y-4" noValidate>
          <ProfileDetailsFields variant="solid" value={profile} onChange={setProfile} />

          {error ? (
            <div role="alert" className={glassAlertClass}>
              {error}
            </div>
          ) : null}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setError(null)
                setStep(1)
              }}
              className={glassGhostBtn}
            >
              {t('common.back')}
            </button>
            <button
              type="submit"
              disabled={calculating || !canSubmitProfile}
              className={`flex-1 ${glassPrimaryBtn}`}
            >
              {calculating ? t('auth.calculatingTdee') : t('auth.calculateTdee')}
            </button>
          </div>
        </form>
      ) : null}

      {step === 3 ? (
        <form onSubmit={handleCreateAccount} className="space-y-4" noValidate>
          <TdeeResultsCard variant="solid" tdee={tdee} />

          {error ? (
            <div role="alert" className={glassAlertClass}>
              {error}
            </div>
          ) : null}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setError(null)
                setStep(2)
              }}
              className={glassGhostBtn}
            >
              {t('common.back')}
            </button>
            <button
              type="submit"
              disabled={submitting || !tdee}
              className={`flex-1 ${glassPrimaryBtn}`}
            >
              {submitting ? t('auth.creatingAccount') : t('common.createAccount')}
            </button>
          </div>
        </form>
      ) : null}
    </GlassAuthFrame>
  )
}
