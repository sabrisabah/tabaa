import { useTranslation } from 'react-i18next'

export default function TdeeResultsCard({ tdee, variant = 'solid' }) {
  const { t } = useTranslation()
  const glass = variant === 'glass'

  if (!tdee) return null

  const macros = [
    { key: 'protein', label: t('tdee.protein'), value: tdee.target_protein, unit: 'g' },
    { key: 'carbs', label: t('tdee.carbs'), value: tdee.target_carbs, unit: 'g' },
    { key: 'fats', label: t('tdee.fats'), value: tdee.target_fats, unit: 'g' },
  ]

  return (
    <div
      className={
        glass
          ? 'overflow-hidden rounded-[1.5rem] border border-white/30 bg-white/10 backdrop-blur-md'
          : 'overflow-hidden rounded-2xl border border-violet-200 bg-gradient-to-b from-violet-50 to-white'
      }
    >
      <div
        className={
          glass
            ? 'border-b border-white/20 px-4 py-3 text-center'
            : 'border-b border-violet-100 px-4 py-3 text-center'
        }
      >
        <p
          className={
            glass
              ? 'text-xs font-semibold uppercase tracking-wider text-white/70'
              : 'text-xs font-semibold uppercase tracking-wider text-violet-700'
          }
        >
          {t('tdee.resultsMethod')}
        </p>
        <h2 className={`mt-1 text-base font-semibold ${glass ? 'text-white' : 'text-slate-900'}`}>
          {t('tdee.resultsTitle')}
        </h2>
      </div>

      <div className="space-y-4 p-4">
        <div className="grid grid-cols-2 gap-3">
          <div
            className={
              glass
                ? 'rounded-2xl border border-white/30 bg-white/10 px-4 py-3 text-center'
                : 'rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center'
            }
          >
            <p className={`text-xs uppercase tracking-wide ${glass ? 'text-white/70' : 'text-slate-500'}`}>
              {t('tdee.bmr')}
            </p>
            <p className={`mt-1 text-2xl font-bold ${glass ? 'text-white' : 'text-slate-900'}`}>
              {Math.round(tdee.bmr)}
            </p>
            <p className={`text-xs ${glass ? 'text-white/60' : 'text-slate-500'}`}>kcal / day</p>
          </div>
          <div
            className={
              glass
                ? 'rounded-2xl border border-white/40 bg-white/20 px-4 py-3 text-center'
                : 'rounded-2xl border border-violet-200 bg-violet-50 px-4 py-3 text-center'
            }
          >
            <p className={`text-xs uppercase tracking-wide ${glass ? 'text-white/80' : 'text-violet-700'}`}>
              {t('tdee.tdee')}
            </p>
            <p className={`mt-1 text-2xl font-bold ${glass ? 'text-white' : 'text-violet-800'}`}>
              {tdee.tdee ?? tdee.target_calories}
            </p>
            <p className={`text-xs ${glass ? 'text-white/70' : 'text-violet-700/80'}`}>kcal / day</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {macros.map((item) => (
            <div
              key={item.key}
              className={
                glass
                  ? 'rounded-xl border border-white/30 bg-white/10 px-2 py-3 text-center'
                  : 'rounded-xl border border-slate-200 bg-white px-2 py-3 text-center'
              }
            >
              <p className={`text-[11px] uppercase tracking-wide ${glass ? 'text-white/70' : 'text-slate-500'}`}>
                {item.label}
              </p>
              <p className={`mt-1 text-lg font-bold ${glass ? 'text-white' : 'text-slate-900'}`}>
                {item.value}
                <span className={`ms-0.5 text-xs font-medium ${glass ? 'text-white/60' : 'text-slate-500'}`}>
                  {item.unit}
                </span>
              </p>
            </div>
          ))}
        </div>

        <p className={`text-center text-xs leading-relaxed ${glass ? 'text-white/70' : 'text-slate-500'}`}>
          {t('tdee.resultsFooter')}
        </p>
      </div>
    </div>
  )
}
