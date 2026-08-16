import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchMyProfile, previewTdee, updateMyProfile } from '../../api/profile'
import { formatAuthError } from '../auth/AuthShell'
import GlassSelect from '../auth/GlassSelect'

const ACTIVITY_OPTIONS = [
  { value: 'sedentary', labelKey: 'profile.sedentary' },
  { value: 'lightly_active', labelKey: 'profile.lightlyActive' },
  { value: 'moderately_active', labelKey: 'profile.moderatelyActive' },
  { value: 'very_active', labelKey: 'profile.veryActive' },
  { value: 'extra_active', labelKey: 'profile.extraActive' },
]

const DEFICIT_OPTIONS = [
  { value: 0, labelKey: 'tdee.maintain', hintKey: 'tdee.maintainHint' },
  { value: 250, labelKey: 'tdee.mild', hintKey: 'tdee.mildHint' },
  { value: 500, labelKey: 'tdee.healthy', hintKey: 'tdee.healthyHint' },
  { value: 750, labelKey: 'tdee.aggressive', hintKey: 'tdee.aggressiveHint' },
]

const glassField =
  'mt-1.5 w-full rounded-full border border-white/55 bg-white/10 px-4 py-3 text-sm text-white outline-none backdrop-blur-sm placeholder:text-white/55 focus:border-white focus:ring-2 focus:ring-white/20'

const glassCard =
  'rounded-[24px] border border-white/25 bg-white/10 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] backdrop-blur-md sm:p-6'

function FormulaPill({ label, sub, tone }) {
  const tones = {
    blue: 'border-sky-200/40 bg-sky-400/20 text-sky-50',
    teal: 'border-teal-200/40 bg-teal-400/20 text-teal-50',
    orange: 'border-orange-200/40 bg-orange-400/20 text-orange-50',
    navy: 'border-white/35 bg-white/15 text-white',
  }
  return (
    <div className={`min-w-[7.5rem] flex-1 rounded-2xl border px-3 py-3 text-center backdrop-blur-sm ${tones[tone]}`}>
      <p className="text-[11px] font-bold uppercase tracking-wide opacity-80">{label}</p>
      <p className="mt-1 text-lg font-extrabold">{sub}</p>
    </div>
  )
}

const HOW_TO_STEPS = [
  {
    step: '1',
    titleKey: 'tdee.step1Title',
    bodyKey: 'tdee.step1Body',
    image: '/tdee/step-1-estimate.png',
    alt: 'Calculator estimating daily calorie needs',
  },
  {
    step: '2',
    titleKey: 'tdee.step2Title',
    bodyKey: 'tdee.step2Body',
    image: '/tdee/step-2-deficit.png',
    alt: 'Phone showing a calorie deficit goal chart',
  },
  {
    step: '3',
    titleKey: 'tdee.step3Title',
    bodyKey: 'tdee.step3Body',
    image: '/tdee/step-3-healthy.png',
    alt: 'Athlete choosing healthy food options',
  },
  {
    step: '4',
    titleKey: 'tdee.step4Title',
    bodyKey: 'tdee.step4Body',
    image: '/tdee/step-4-monitor.png',
    alt: 'Progress monitoring with strength and fat-loss focus',
  },
]

export default function TdeeCalculator({
  onTargetsApplied,
  initialProfile = null,
  applyTargets = null,
  showHowTo = true,
  applyLabel = null,
}) {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    age: '',
    gender: 'male',
    weight_kg: '',
    height_cm: '',
    activity_level: 'moderately_active',
  })
  const [deficit, setDeficit] = useState(500)
  const [result, setResult] = useState(null)
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [calculating, setCalculating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [savedMessage, setSavedMessage] = useState(null)

  useEffect(() => {
    let cancelled = false

    function hydrate(profile) {
      setForm({
        age: String(profile?.age ?? ''),
        gender: profile?.gender || 'male',
        weight_kg: String(profile?.weight_kg ?? ''),
        height_cm: String(profile?.height_cm ?? ''),
        activity_level: profile?.activity_level || 'moderately_active',
      })
      setResult(null)
      setError(null)
      setSavedMessage(null)
      setLoadingProfile(false)
    }

    if (initialProfile) {
      hydrate(initialProfile)
      return () => {
        cancelled = true
      }
    }

    ;(async () => {
      try {
        const profile = await fetchMyProfile()
        if (cancelled) return
        hydrate(profile)
      } catch {
        if (!cancelled) setLoadingProfile(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [initialProfile])

  const canCalculate = useMemo(() => {
    return (
      Number(form.age) >= 13 &&
      Number(form.weight_kg) > 0 &&
      Number(form.height_cm) > 0 &&
      (form.gender === 'male' || form.gender === 'female') &&
      form.activity_level
    )
  }, [form])

  const genderOptions = useMemo(
    () => [
      { value: 'male', label: t('profile.male') },
      { value: 'female', label: t('profile.female') },
    ],
    [t],
  )

  const activityOptions = useMemo(
    () => ACTIVITY_OPTIONS.map((option) => ({ value: option.value, label: t(option.labelKey) })),
    [t],
  )

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setSavedMessage(null)
  }

  async function runCalculate(nextDeficit = deficit) {
    setError(null)
    setSavedMessage(null)
    if (!canCalculate) {
      setError(t('tdee.fillRequired'))
      return
    }

    setCalculating(true)
    try {
      const data = await previewTdee({
        age: Number(form.age),
        gender: form.gender,
        weight_kg: Number(form.weight_kg),
        height_cm: Number(form.height_cm),
        activity_level: form.activity_level,
        deficit: nextDeficit,
      })
      setResult(data)
    } catch (err) {
      setError(formatAuthError(err, t('tdee.couldNotCalculate')))
    } finally {
      setCalculating(false)
    }
  }

  async function handleCalculate(event) {
    event.preventDefault()
    await runCalculate(deficit)
  }

  async function handleDeficitChange(value) {
    setDeficit(value)
    if (result) {
      await runCalculate(value)
    }
  }

  async function handleApplyTargets() {
    if (!result) return
    setSaving(true)
    setError(null)
    setSavedMessage(null)
    try {
      const payload = {
        age: Number(form.age),
        gender: form.gender,
        weight_kg: Number(form.weight_kg),
        height_cm: Number(form.height_cm),
        activity_level: form.activity_level,
        target_calories: result.target_calories ?? result.goal_calories,
        target_protein: result.target_protein,
        target_carbs: result.target_carbs,
        target_fats: result.target_fats,
      }
      if (applyTargets) {
        await applyTargets(payload, result)
      } else {
        await updateMyProfile(payload)
      }
      setSavedMessage(t('tdee.saved'))
      onTargetsApplied?.(payload, result)
    } catch (err) {
      setError(formatAuthError(err, t('tdee.couldNotSave')))
    } finally {
      setSaving(false)
    }
  }

  const maintenance = result?.maintenance_calories ?? result?.tdee
  const goal = result?.goal_calories ?? result?.target_calories

  return (
    <section className="space-y-5">
      <div
        className="overflow-visible rounded-[28px] border border-white/25 p-5 shadow-[0_40px_100px_-30px_rgba(30,0,80,0.55)] sm:p-8"
        style={{
          background:
            'radial-gradient(circle at 15% 10%, rgba(167,139,250,0.45), transparent 40%), radial-gradient(circle at 90% 80%, rgba(124,58,237,0.35), transparent 45%), linear-gradient(145deg, #4c1d95 0%, #6d28d9 48%, #5b21b6 100%)',
        }}
      >
        <div className="mb-8 w-full text-center">
          <h2 className="mx-auto text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            {t('tdee.title')}
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-white/75 sm:text-base">
            {t('tdee.subtitle')}
          </p>
        </div>

        <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <form onSubmit={handleCalculate} className={`${glassCard} overflow-visible`} noValidate>
            {loadingProfile ? (
              <p className="mb-3 text-sm text-white/70">{t('tdee.loadingProfile')}</p>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-white/85">{t('tdee.age')}</span>
                <input
                  type="number"
                  min="13"
                  max="120"
                  value={form.age}
                  onChange={(e) => update('age', e.target.value)}
                  className={glassField}
                  placeholder={t('tdee.age')}
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-medium text-white/85">{t('tdee.sex')}</span>
                <GlassSelect
                  value={form.gender}
                  options={genderOptions}
                  onChange={(value) => update('gender', value)}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-white/85">{t('tdee.weightKg')}</span>
                <input
                  type="number"
                  min="1"
                  step="0.1"
                  value={form.weight_kg}
                  onChange={(e) => update('weight_kg', e.target.value)}
                  className={glassField}
                  placeholder={t('tdee.weightKg')}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-white/85">{t('tdee.heightCm')}</span>
                <input
                  type="number"
                  min="50"
                  max="300"
                  step="0.1"
                  value={form.height_cm}
                  onChange={(e) => update('height_cm', e.target.value)}
                  className={glassField}
                  placeholder={t('tdee.heightCm')}
                />
              </label>
            </div>

            <label className="mt-4 block">
              <span className="mb-1.5 block text-sm font-medium text-white/85">{t('tdee.activityLevel')}</span>
              <GlassSelect
                className="w-full"
                value={form.activity_level}
                options={activityOptions}
                placement="top"
                onChange={(value) => update('activity_level', value)}
              />
            </label>

            {error ? (
              <p className="mt-4 rounded-2xl border border-rose-200/40 bg-rose-500/20 px-3 py-2 text-sm text-white">
                {error}
              </p>
            ) : null}
            {savedMessage ? (
              <p className="mt-4 rounded-2xl border border-emerald-200/40 bg-emerald-400/20 px-3 py-2 text-sm text-white">
                {savedMessage}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={calculating || !canCalculate}
              className="mt-5 w-full rounded-full bg-white px-4 py-3.5 text-sm font-bold text-slate-800 shadow-lg shadow-violet-950/30 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {calculating ? t('tdee.calculating') : t('tdee.estimate')}
            </button>
          </form>

          <div className="space-y-4">
            <div className={glassCard}>
              <p className="text-center text-xs font-bold uppercase tracking-wider text-white/70">
                {t('tdee.formula')}
              </p>
              <div className="mt-3 flex flex-wrap items-stretch justify-center gap-2">
                <FormulaPill
                  label={t('tdee.bmr')}
                  sub={result ? `${result.bmr_kcal ?? Math.round(result.bmr)}` : '—'}
                  tone="blue"
                />
                <span className="self-center text-lg font-bold text-white/50">+</span>
                <FormulaPill label={t('tdee.tea')} sub={result ? `${result.tea}` : '—'} tone="teal" />
                <span className="self-center text-lg font-bold text-white/50">+</span>
                <FormulaPill label={t('tdee.tef')} sub={result ? `${result.tef}` : '—'} tone="orange" />
                <span className="self-center text-lg font-bold text-white/50">=</span>
                <FormulaPill label={t('tdee.tdee')} sub={result ? `${maintenance}` : '—'} tone="navy" />
              </div>
              <div className="mt-4 grid gap-2 text-xs text-white/75 sm:grid-cols-3">
                <p className="rounded-xl border border-white/15 bg-white/10 px-3 py-2">{t('tdee.bmrHint')}</p>
                <p className="rounded-xl border border-white/15 bg-white/10 px-3 py-2">{t('tdee.teaHint')}</p>
                <p className="rounded-xl border border-white/15 bg-white/10 px-3 py-2">{t('tdee.tefHint')}</p>
              </div>
            </div>

            {result ? (
              <div className={glassCard}>
                <p className="text-sm font-semibold text-white">{t('tdee.setDeficit')}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {DEFICIT_OPTIONS.map((option) => {
                    const selected = deficit === option.value
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => handleDeficitChange(option.value)}
                        className={`rounded-2xl border px-3 py-3 text-left transition ${
                          selected
                            ? 'border-white bg-white/25 text-white ring-1 ring-white/40'
                            : 'border-white/25 bg-white/10 text-white/85 hover:bg-white/15'
                        }`}
                      >
                        <span className="block text-sm font-bold">{t(option.labelKey)}</span>
                        <span className="mt-0.5 block text-xs opacity-80">
                          {option.hintKey ? t(option.hintKey) : option.hint}
                        </span>
                      </button>
                    )
                  })}
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-rose-200/35 bg-rose-400/20 px-4 py-3">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-rose-100">
                      {t('tdee.highCalories')}
                    </p>
                    <p className="mt-1 text-sm font-semibold text-white">{maintenance + 400} kcal</p>
                    <p className="mt-1 text-xs text-rose-50/80">{t('tdee.surplus')}</p>
                  </div>
                  <div className="rounded-2xl border border-orange-200/35 bg-orange-400/20 px-4 py-3">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-orange-100">
                      {t('tdee.deficitCalories')}
                    </p>
                    <p className="mt-1 text-2xl font-extrabold text-white">{goal} kcal</p>
                    <p className="mt-1 text-xs text-orange-50/80">
                      {t('tdee.healthyDeficit')}
                      {deficit ? `, −${deficit}` : ` ${t('tdee.maintenance')}`}
                    </p>
                  </div>
                </div>

                <p className="mt-3 text-center text-xs text-white/75">
                  {t('tdee.protein')} {result.target_protein}g · {t('tdee.carbs')} {result.target_carbs}g ·{' '}
                  {t('tdee.fats')} {result.target_fats}g
                </p>

                <button
                  type="button"
                  onClick={handleApplyTargets}
                  disabled={saving}
                  className="mt-4 w-full rounded-full bg-white px-4 py-3 text-sm font-bold text-slate-800 transition hover:bg-violet-50 disabled:opacity-60"
                >
                  {saving ? t('common.saving') : applyLabel || t('tdee.apply')}
                </button>
              </div>
            ) : (
              <div className="rounded-[24px] border border-dashed border-white/35 bg-white/5 px-5 py-8 text-center text-sm text-white/75 backdrop-blur-sm">
                {t('tdee.unlock')}
              </div>
            )}
          </div>
        </div>
      </div>

      {showHowTo ? (
        <div
          className="overflow-hidden rounded-[28px] border border-white/25 p-5 shadow-[0_30px_80px_-28px_rgba(30,0,80,0.45)] sm:p-7"
          style={{
            background:
              'linear-gradient(160deg, rgba(76,29,149,0.92), rgba(109,40,217,0.88) 55%, rgba(91,33,182,0.9))',
          }}
        >
          <div className="mx-auto max-w-3xl text-center">
            <h3 className="text-2xl font-extrabold text-white sm:text-3xl">{t('tdee.howTitle')}</h3>
            <p className="mt-2 text-sm text-white/70">{t('tdee.howSubtitle')}</p>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {HOW_TO_STEPS.map((item) => (
              <article
                key={item.step}
                className="group relative overflow-hidden rounded-[24px] border border-white/25 bg-white/10 shadow-lg backdrop-blur-md transition hover:-translate-y-1"
              >
                <div className="relative aspect-square overflow-hidden bg-violet-950/40">
                  <img
                    src={item.image}
                    alt={item.alt}
                    className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
                    loading="lazy"
                  />
                  <div className="absolute left-3 top-3 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-violet-900 shadow-md">
                    {t('tdee.step')} {item.step}
                  </div>
                </div>
                <div className="space-y-1.5 px-4 py-4">
                  <h4 className="text-sm font-bold text-white">{t(item.titleKey)}</h4>
                  <p className="text-xs leading-relaxed text-white/70">{t(item.bodyKey)}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
