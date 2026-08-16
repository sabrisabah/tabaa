import { useTranslation } from 'react-i18next'

function formatMacro(value) {
  return Math.round(Number(value) || 0)
}

export default function MealSection({ mealType, logs, onAddFood, onRemoveLog }) {
  const { t } = useTranslation()
  const label = t(`meals.${mealType}`, { defaultValue: mealType })
  const sectionCalories = logs.reduce((sum, log) => {
    const qty = Number(log.quantity) || 0
    const cal = Number(log.food_item?.calories) || 0
    return sum + qty * cal
  }, 0)

  return (
    <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 sm:px-5">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{label}</h3>
          <p className="text-xs text-slate-500">
            {t('meals.kcalLogged', { count: formatMacro(sectionCalories) })}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onAddFood(mealType)}
          className="rounded-xl bg-emerald-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 active:scale-[0.98]"
        >
          {t('meals.addFood')}
        </button>
      </div>

      {logs.length === 0 ? (
        <p className="px-4 py-6 text-sm text-slate-400 sm:px-5">
          {t('meals.empty')}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {logs.map((log) => {
            const food = log.food_item
            const qty = Number(log.quantity) || 0
            const calories = qty * (Number(food?.calories) || 0)

            return (
              <li
                key={log.id}
                className="flex items-start justify-between gap-3 px-4 py-3 sm:px-5"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-800">{food?.name}</p>
                  {food?.brand ? (
                    <p className="truncate text-xs text-slate-500">{food.brand}</p>
                  ) : null}
                  <p className="mt-1 text-xs text-slate-500">
                    {qty} × {food?.serving_size}
                    {food?.serving_unit} · P {formatMacro(qty * food?.protein)}g · C{' '}
                    {formatMacro(qty * food?.carbs)}g · F {formatMacro(qty * food?.fats)}g
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <span className="text-sm font-semibold text-slate-700">
                    {formatMacro(calories)} kcal
                  </span>
                  <button
                    type="button"
                    onClick={() => onRemoveLog(log.id)}
                    className="text-xs font-medium text-rose-500 hover:text-rose-600"
                  >
                    {t('meals.remove')}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
