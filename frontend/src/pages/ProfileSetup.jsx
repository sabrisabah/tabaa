import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createMyProfile } from '../api/profile'
import ProfileDetailsFields, {
  defaultProfileDetails,
  isProfileDetailsValid,
  profileDetailsToPayload,
} from '../components/auth/ProfileDetailsFields'
import { formatAuthError } from '../components/auth/AuthShell'
import { GlassAuthFrame, glassAlertClass, glassPrimaryBtn } from '../components/auth/GlassAuthFrame'

export default function ProfileSetup({ onComplete }) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const [profile, setProfile] = useState(defaultProfileDetails)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = useMemo(() => isProfileDetailsValid(profile), [profile])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return

    setSubmitting(true)
    setError(null)
    try {
      await createMyProfile(profileDetailsToPayload(profile))
      onComplete()
    } catch (err) {
      setError(formatAuthError(err, 'Could not save your profile. Please check the values.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <GlassAuthFrame
      dir={isAr ? 'rtl' : 'ltr'}
      title={t('profile.completeTitle')}
      subtitle={t('profile.completeBody')}
      wide
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <ProfileDetailsFields variant="solid" value={profile} onChange={setProfile} />

        {error ? (
          <p className={glassAlertClass}>
            {error}
          </p>
        ) : null}

        <button type="submit" disabled={!canSubmit || submitting} className={glassPrimaryBtn}>
          {submitting ? t('common.saving') : t('profile.saveOpen')}
        </button>
      </form>
    </GlassAuthFrame>
  )
}
