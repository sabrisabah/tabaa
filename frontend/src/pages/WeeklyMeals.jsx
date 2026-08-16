import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchWeeklyMealPlan } from '../api/mealplans'
import LanguageSwitcher from '../components/LanguageSwitcher'
import {
  glassBtnGhost,
  glassBtnWhite,
  glassCard,
  glassHeader,
  glassPageBg,
  glassStat,
} from '../styles/glassTheme'

export default function WeeklyMeals({ onBack, onOpenSubscriptions }) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [forbidden, setForbidden] = useState(false)
  const [plan, setPlan] = useState(null)
  const [selectedDay, setSelectedDay] = useState(1)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      setForbidden(false)
      try {
        const data = await fetchWeeklyMealPlan()
        if (!cancelled) {
          setPlan(data)
          setSelectedDay(data.days?.[0]?.day ?? 1)
        }
      } catch (err) {
        if (cancelled) return
        if (err?.response?.status === 403) {
          setForbidden(true)
          setError(t('meals.subscriptionRequired'))
        } else {
          setError(err?.response?.data?.detail || t('meals.loadError'))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [t])

  const day = plan?.days?.find((d) => d.day === selectedDay)
  const deficitCalories = plan?.deficit_calories ?? plan?.target_calories
  const fixedDeficit = plan?.fixed_deficit ?? plan?.deficit ?? 500

  return (
    <div className="min-h-screen" style={glassPageBg} dir={isAr ? 'rtl' : 'ltr'}>
      <header className={glassHeader}>
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-wider text-white/70">{t('common.appName')}</p>
            <h1 className="text-xl font-bold tracking-tight">{t('meals.title')}</h1>
            {plan ? (
              <p className="text-sm text-white/85">
                {isAr ? plan.program_ar : plan.program_en} · {plan.weight_kg} {t('meals.kg')}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button type="button" onClick={onBack} className={glassBtnWhite}>
              {isAr ? '→' : '←'} {t('common.back')}
            </button>
            <div className="rounded-full bg-white/10 p-1 ring-1 ring-white/20">
              <LanguageSwitcher variant="glass" />
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6">
        {loading ? <p className="text-sm text-white/80">{t('common.loading')}</p> : null}

        {forbidden ? (
          <div className={`${glassCard} p-6 text-center`}>
            <p className="text-sm text-white">{error}</p>
            <button type="button" onClick={onOpenSubscriptions} className={`mt-4 ${glassBtnWhite}`}>
              {t('subscriptions.title')}
            </button>
          </div>
        ) : null}

        {!loading && !forbidden && error ? <p className="text-sm text-rose-200">{error}</p> : null}

        {plan && !forbidden ? (
          <>
            <section className={`${glassCard} grid gap-3 p-4 sm:grid-cols-4`}>
              <Stat label={t('meals.tdee')} value={`${plan.tdee ?? '—'} ${t('meals.kcal')}`} hint={t('meals.tdeeHint')} />
              <Stat
                label={t('meals.deficitAmount')}
                value={`−${fixedDeficit} ${t('meals.kcal')}`}
                hint={t('meals.deficitAmountHint')}
                tone="orange"
              />
              <Stat
                label={t('meals.deficitCalories')}
                value={`${deficitCalories} ${t('meals.kcalDay')}`}
                hint={t('meals.deficitCaloriesHint')}
                tone="orange"
              />
              <Stat label={t('meals.scale')} value={`×${plan.scale_factor}`} hint={t('meals.scaleHint')} />
            </section>

            <p className="rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white/90">
              {isAr ? plan.note_ar : plan.note_en}
            </p>

            <div className="flex gap-2 overflow-x-auto pb-1">
              {plan.days.map((d) => {
                const active = d.day === selectedDay
                return (
                  <button
                    key={d.day}
                    type="button"
                    onClick={() => setSelectedDay(d.day)}
                    className={`shrink-0 rounded-full px-3 py-2 text-sm font-semibold transition ${
                      active ? glassBtnWhite : glassBtnGhost
                    }`}
                  >
                    {isAr ? d.name_ar : d.name_en}
                  </button>
                )
              })}
            </div>

            {day ? (
              <>
                <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <MacroChip label={t('meals.dayTarget')} value={`${day.targets.calories}`} tone="orange" />
                  <MacroChip
                    label={`${t('meals.protein')} ${day.targets.protein_pct}%`}
                    value={`${day.targets.protein_g}g`}
                  />
                  <MacroChip
                    label={`${t('meals.carbs')} ${day.targets.carbs_pct}%`}
                    value={`${day.targets.carbs_g}g`}
                  />
                  <MacroChip
                    label={`${t('meals.fats')} ${day.targets.fats_pct}%`}
                    value={`${day.targets.fats_g}g`}
                    tone="orange"
                  />
                </section>

                <section className={`${glassCard} overflow-hidden`}>
                  <div className="border-b border-white/15 bg-white/10 px-4 py-3">
                    <h2 className="text-sm font-bold text-white">{t('meals.tableTitle')}</h2>
                    <p className="text-xs text-white/70">
                      {t('meals.tableSubtitle', {
                        total: day.meals_calories_total ?? day.meals.reduce((s, m) => s + m.calories, 0),
                        target: deficitCalories,
                      })}
                    </p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm text-white">
                      <thead className="bg-white/15 text-xs uppercase tracking-wide text-white/90">
                        <tr>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.colMeal')}</th>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.colDish')}</th>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.colCalories')}</th>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.colQuantity')}</th>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.protein')}</th>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.carbs')}</th>
                          <th className="px-3 py-2.5 text-start font-semibold">{t('meals.fats')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {day.meals.map((meal, idx) => (
                          <tr
                            key={meal.slot}
                            className={`align-top border-t border-white/10 ${
                              idx % 2 === 0 ? 'bg-white/5' : 'bg-white/10'
                            }`}
                          >
                            <td className="px-3 py-3 font-semibold text-amber-200">
                              {isAr ? meal.label_ar : meal.label_en}
                            </td>
                            <td className="px-3 py-3">
                              <p className="font-semibold text-white">
                                {isAr ? meal.title_ar : meal.title_en}
                              </p>
                              <p className="mt-0.5 text-xs text-white/65">
                                {isAr ? meal.description_ar : meal.description_en}
                              </p>
                            </td>
                            <td className="whitespace-nowrap px-3 py-3 font-bold text-amber-200">
                              {meal.calories} {t('meals.kcal')}
                            </td>
                            <td className="px-3 py-3 text-white/90">
                              <p className="font-medium">{isAr ? meal.quantity_ar : meal.quantity_en}</p>
                            </td>
                            <td className="whitespace-nowrap px-3 py-3 text-white/85">{meal.protein_g}g</td>
                            <td className="whitespace-nowrap px-3 py-3 text-white/85">{meal.carbs_g}g</td>
                            <td className="whitespace-nowrap px-3 py-3 text-white/85">{meal.fats_g}g</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            ) : null}
          </>
        ) : null}
      </main>
    </div>
  )
}

function Stat({ label, value, hint, tone = 'blue' }) {
  return (
    <div className={glassStat}>
      <p className="text-[11px] font-medium text-white/65">{label}</p>
      <p className={`text-lg font-bold ${tone === 'orange' ? 'text-amber-300' : 'text-white'}`}>{value}</p>
      {hint ? <p className="mt-0.5 text-[11px] leading-snug text-white/55">{hint}</p> : null}
    </div>
  )
}

function MacroChip({ label, value, tone = 'blue' }) {
  return (
    <div className={glassStat}>
      <p className="text-xs text-white/65">{label}</p>
      <p className={`text-lg font-bold ${tone === 'orange' ? 'text-amber-300' : 'text-white'}`}>{value}</p>
    </div>
  )
}
