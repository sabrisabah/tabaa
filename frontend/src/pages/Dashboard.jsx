import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import MacroBars from '../components/charts/MacroBars'
import MacroRing from '../components/charts/MacroRing'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SubscriptionCalendar from '../components/subscriptions/SubscriptionCalendar'
import SubscriptionsPanel from '../components/subscriptions/SubscriptionsPanel'
import TdeeCalculator from '../components/tdee/TdeeCalculator'
import WeightLossChart from '../components/charts/WeightLossChart'
import { fetchSubscriptionStatus } from '../api/subscriptions'
import { addWeightLog, fetchWeightLogs } from '../api/weight'
import { fetchMyProfile } from '../api/profile'
import { useDiary, EMPTY_MACROS } from '../context/DiaryContext'
import ProfileSetup from './ProfileSetup'
import PatientPlanCard from '../components/plans/PatientPlanCard'
import {
  glassBtnGhost,
  glassBtnWhite,
  glassCard,
  glassHeader,
  glassInput,
  glassPageBg,
  glassStat,
} from '../styles/glassTheme'

function SummaryStat({ label, value, sub, tone = 'blue' }) {
  const valueColor = tone === 'orange' ? 'text-amber-300' : 'text-violet-100'
  return (
    <div className={glassStat}>
      <p className="text-xs font-medium uppercase tracking-wide text-white/65">{label}</p>
      <p className={`text-lg font-bold ${valueColor}`}>{value}</p>
      {sub ? <p className="text-xs text-white/55">{sub}</p> : null}
    </div>
  )
}

function SectionCard({ title, subtitle, children }) {
  return (
    <section className={glassCard}>
      <div className="p-4 sm:p-5">
        {title ? (
          <header className="mb-4">
            <h2 className="text-base font-bold text-white">{title}</h2>
            {subtitle ? <p className="mt-1 text-sm text-white/70">{subtitle}</p> : null}
          </header>
        ) : null}
        {children}
      </div>
    </section>
  )
}

export default function Dashboard({
  onLogout,
  onOpenMeals,
  forceOpenSubscriptions = false,
  onSubscriptionsOpened,
  clinicRole = null,
  onOpenClinic,
}) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const {
    summary,
    loading,
    error,
    needsProfile,
    refreshDashboard,
  } = useDiary()

  const [subsOpen, setSubsOpen] = useState(false)
  const [hasMealAccess, setHasMealAccess] = useState(false)
  const [needsRenewal, setNeedsRenewal] = useState(false)
  const [calendarInfo, setCalendarInfo] = useState(null)
  const [promo, setPromo] = useState(null)
  const [weightProgress, setWeightProgress] = useState(null)
  const [weightLogs, setWeightLogs] = useState([])
  const [newWeight, setNewWeight] = useState('')
  const [weightMsg, setWeightMsg] = useState('')
  const [showTdeeCalculator, setShowTdeeCalculator] = useState(false)

  async function refreshWeightLogs() {
    try {
      const logs = await fetchWeightLogs()
      setWeightLogs(Array.isArray(logs) ? logs : [])
    } catch {
      setWeightLogs([])
    }
  }

  async function refreshSubscription() {
    try {
      const data = await fetchSubscriptionStatus()
      setHasMealAccess(Boolean(data.has_meal_access))
      setNeedsRenewal(Boolean(data.needs_renewal))
      setCalendarInfo(data.calendar || null)
      setPromo(data.promo_banner || null)
      setWeightProgress(data.weight_progress || null)
      if (data.weight_progress?.current_weight_kg) {
        setNewWeight(String(data.weight_progress.current_weight_kg))
      }
      if (data.has_meal_access) {
        await refreshWeightLogs()
      }
    } catch {
      setHasMealAccess(false)
      setNeedsRenewal(false)
      setCalendarInfo(null)
    }
  }

  useEffect(() => {
    refreshSubscription()
    let cancelled = false
    fetchMyProfile()
      .then((profile) => {
        if (!cancelled) setShowTdeeCalculator(Boolean(profile?.show_tdee_calculator))
      })
      .catch(() => {
        if (!cancelled) setShowTdeeCalculator(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (forceOpenSubscriptions) {
      setSubsOpen(true)
      onSubscriptionsOpened?.()
    }
  }, [forceOpenSubscriptions, onSubscriptionsOpened])

  async function handleSaveWeight(e) {
    e.preventDefault()
    const value = Number(newWeight)
    if (!value || value < 1) return
    setWeightMsg('')
    try {
      const today = new Date().toISOString().slice(0, 10)
      await addWeightLog({ weight_kg: value, recorded_at: today })
      setWeightMsg(t('weight.saved'))
      await refreshSubscription()
      await refreshWeightLogs()
      await refreshDashboard()
    } catch {
      setWeightMsg(t('weight.saveError'))
    }
  }

  const consumed = summary?.consumed ?? EMPTY_MACROS
  const targets = summary?.targets ?? EMPTY_MACROS
  const remaining = summary?.remaining ?? EMPTY_MACROS
  const showCalendar = calendarInfo?.starts_at && calendarInfo?.ends_at

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={glassPageBg}>
        <div className="text-center text-white">
          <div className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-4 border-white/20 border-t-white" />
          <p className="text-sm text-white/80">{t('dashboard.loadingDiary')}</p>
        </div>
      </div>
    )
  }

  if (needsProfile) {
    return <ProfileSetup onComplete={refreshDashboard} />
  }

  if (error) {
    const isAuthError =
      typeof error === 'string' &&
      /credentials were not provided|authentication|unauthorized|token|not authenticated/i.test(error)

    if (isAuthError) {
      if (typeof window !== 'undefined') {
        window.setTimeout(() => window.dispatchEvent(new CustomEvent('auth:logout')), 0)
      }
      return (
        <div className="grid min-h-screen place-items-center" style={glassPageBg}>
          <p className="text-sm text-white">جاري فتح تسجيل الدخول…</p>
        </div>
      )
    }

    return (
      <div className="flex min-h-screen items-center justify-center p-4" style={glassPageBg} dir={isAr ? 'rtl' : 'ltr'}>
        <div className={`${glassCard} w-full max-w-md p-8 text-center`}>
          <h2 className="text-lg font-bold text-white">{t('common.appName')}</h2>
          <p className="mt-2 text-sm text-white/75">{error}</p>
          <button type="button" onClick={refreshDashboard} className={`mt-5 ${glassBtnWhite}`}>
            {t('common.retry')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={glassPageBg} dir={isAr ? 'rtl' : 'ltr'}>
      {hasMealAccess && promo ? (
        <div className="border-b border-white/15 bg-white/10 text-white backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm sm:px-6">
            <p className="font-semibold">{promo.name}</p>
            <p className="truncate text-white/85">{isAr ? promo.text_ar : promo.text_en}</p>
          </div>
        </div>
      ) : null}

      <header className={glassHeader}>
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-white/70">
                {t('common.appName')}
              </p>
              <h1 className="text-xl font-bold tracking-tight sm:text-2xl">{t('dashboard.title')}</h1>
              {summary?.date ? <p className="text-sm text-white/80">{summary.date}</p> : null}
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {(clinicRole === 'doctor' || clinicRole === 'secretary') && onOpenClinic ? (
                <button type="button" onClick={onOpenClinic} className={glassBtnGhost}>
                  د. طيبة
                </button>
              ) : null}
              <button type="button" onClick={() => setSubsOpen(true)} className={glassBtnWhite}>
                {t('subscriptions.title')}
              </button>
              <button
                type="button"
                disabled={!hasMealAccess}
                onClick={() => {
                  if (hasMealAccess) onOpenMeals?.()
                }}
                title={hasMealAccess ? t('meals.title') : t('meals.lockedUntilAdmin')}
                className={`${glassBtnGhost} disabled:cursor-not-allowed disabled:opacity-40`}
              >
                {t('meals.programButton')}
              </button>
              <div className="rounded-full bg-white/10 p-1 ring-1 ring-white/20">
                <LanguageSwitcher variant="glass" />
              </div>
              {onLogout ? (
                <button type="button" onClick={onLogout} className={glassBtnGhost}>
                  {t('common.signOut')}
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <div className="min-w-0 flex-1 space-y-6">
            <PatientPlanCard />
            {showTdeeCalculator ? <TdeeCalculator onTargetsApplied={refreshDashboard} /> : null}

            {hasMealAccess && weightProgress ? (
              <SectionCard title={t('weight.title')} subtitle={t('weight.subtitle')}>
                <div className="grid grid-cols-3 gap-3">
                  <SummaryStat
                    label={t('weight.start')}
                    value={`${weightProgress.starting_weight_kg ?? '—'} ${t('weight.kg')}`}
                  />
                  <SummaryStat
                    label={t('weight.current')}
                    value={`${weightProgress.current_weight_kg} ${t('weight.kg')}`}
                  />
                  <SummaryStat
                    label={t('weight.lost')}
                    value={`${weightProgress.lost_kg} ${t('weight.kg')}`}
                    tone="orange"
                  />
                </div>
                {weightProgress.gift_eligible ? (
                  <p className="mt-3 rounded-xl border border-amber-200/40 bg-amber-400/20 px-3 py-2 text-sm font-semibold text-amber-50">
                    {t('weight.giftReady')}
                  </p>
                ) : (
                  <p className="mt-3 text-xs text-white/65">{t('weight.giftHint')}</p>
                )}
                <div className="mt-4 grid gap-4 sm:grid-cols-2 sm:items-stretch">
                  <div className={isAr ? 'sm:order-2' : undefined}>
                    <WeightLossChart logs={weightLogs} progress={weightProgress} />
                  </div>
                  <div className={`flex flex-col justify-center ${isAr ? 'sm:order-1' : ''}`}>
                    <form onSubmit={handleSaveWeight} className="flex flex-wrap gap-2">
                      <input
                        type="number"
                        step="0.1"
                        min="1"
                        value={newWeight}
                        onChange={(e) => setNewWeight(e.target.value)}
                        className={`${glassInput} w-32`}
                        placeholder={t('weight.current')}
                      />
                      <button type="submit" className={glassBtnWhite}>
                        {t('weight.save')}
                      </button>
                    </form>
                    {weightMsg ? <p className="mt-2 text-xs text-white/75">{weightMsg}</p> : null}
                  </div>
                </div>
              </SectionCard>
            ) : null}

            <SectionCard title={t('dashboard.todayProgress')}>
              <div className="grid gap-4 lg:grid-cols-[auto_1fr] lg:items-start">
                <div className="flex justify-center rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur-sm">
                  <MacroRing
                    consumed={consumed.calories}
                    target={targets.calories}
                    label={t('dashboard.calories')}
                    color="#ddd6fe"
                  />
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <SummaryStat
                      label={t('dashboard.remaining')}
                      value={`${Math.round(remaining.calories)}`}
                      sub={t('dashboard.kcalLeft')}
                      tone="orange"
                    />
                    <SummaryStat
                      label={t('dashboard.proteinLeft')}
                      value={`${Math.round(remaining.protein)}g`}
                    />
                    <SummaryStat
                      label={t('dashboard.carbsLeft')}
                      value={`${Math.round(remaining.carbs)}g`}
                    />
                    <SummaryStat
                      label={t('dashboard.fatsLeft')}
                      value={`${Math.round(remaining.fats)}g`}
                      tone="orange"
                    />
                  </div>
                  <MacroBars consumed={consumed} targets={targets} />
                </div>
              </div>
            </SectionCard>

            {!hasMealAccess ? (
              <section className={`${glassCard} p-5 text-center`}>
                <p className="text-sm text-white">
                  {needsRenewal ? t('subscriptions.renewRequired') : t('meals.lockedHint')}
                </p>
                <p className="mt-2 text-xs text-white/70">
                  {needsRenewal ? t('subscriptions.renewAdminNote') : t('subscriptions.unlockMeals')}
                </p>
                <button type="button" onClick={() => setSubsOpen(true)} className={`mt-4 ${glassBtnWhite}`}>
                  {needsRenewal ? t('calendar.renewCta') : t('subscriptions.title')}
                </button>
              </section>
            ) : null}
          </div>

          {showCalendar ? (
            <aside
              className={`w-full shrink-0 lg:sticky lg:top-6 lg:w-[300px] lg:self-start ${
                isAr ? 'lg:order-first' : 'lg:order-last'
              }`}
              dir={isAr ? 'rtl' : 'ltr'}
            >
              <SubscriptionCalendar
                startsAt={calendarInfo.starts_at}
                endsAt={calendarInfo.ends_at}
                accessActive={Boolean(calendarInfo.access_active)}
                planName={isAr ? calendarInfo.plan_name_ar : calendarInfo.plan_name_en}
                onRenew={() => setSubsOpen(true)}
              />
            </aside>
          ) : null}
        </div>
      </main>

      <SubscriptionsPanel
        open={subsOpen}
        onClose={() => setSubsOpen(false)}
        onAccessChange={(ok) => {
          setHasMealAccess(ok)
          refreshSubscription()
        }}
      />
    </div>
  )
}
