import { useEffect, useState } from 'react'
import { nutritionPlansApi } from '../../api/clinic'
import { glassCard } from '../../styles/glassTheme'

export default function PatientPlanCard() {
  const [plan, setPlan] = useState(null)

  useEffect(() => {
    let cancelled = false
    nutritionPlansApi
      .mine()
      .then(({ data }) => {
        if (!cancelled) setPlan(data)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  if (!plan?.latest_version) return null
  const v = plan.latest_version
  const meals = v.meal_items || []

  return (
    <section className={glassCard}>
      <div className="p-4 sm:p-5">
        <header className="mb-3">
          <h2 className="text-base font-bold text-white">خطتي من د. طيبة</h2>
          <p className="mt-1 text-sm text-white/70">
            {plan.name} · الإصدار {v.version_number} · {v.calorie_target} سعرة
          </p>
        </header>
        <div className="mb-3 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-xl border border-white/20 bg-white/10 px-2 py-2">
            <div className="text-white/70">بروتين</div>
            <div className="font-bold text-white">{v.protein_g}غ</div>
          </div>
          <div className="rounded-xl border border-white/20 bg-white/10 px-2 py-2">
            <div className="text-white/70">كارب</div>
            <div className="font-bold text-white">{v.carbs_g}غ</div>
          </div>
          <div className="rounded-xl border border-white/20 bg-white/10 px-2 py-2">
            <div className="text-white/70">دهون</div>
            <div className="font-bold text-white">{v.fats_g}غ</div>
          </div>
        </div>
        {v.physician_notes_patient ? (
          <p className="mb-3 rounded-xl border border-white/15 bg-white/10 px-3 py-2 text-sm text-white/85">
            {v.physician_notes_patient}
          </p>
        ) : null}
        <ul className="space-y-2 text-sm">
          {meals.map((m) => (
            <li key={m.id} className="rounded-xl border border-white/15 bg-white/10 px-3 py-2">
              <div className="font-semibold text-white">
                {m.meal_slot} · {m.food_name} ({m.quantity} {m.unit})
              </div>
              {m.alternative_name ? (
                <div className="text-xs text-white/65">بديل: {m.alternative_name}</div>
              ) : null}
              {m.instructions ? <div className="text-xs text-white/70">{m.instructions}</div> : null}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
