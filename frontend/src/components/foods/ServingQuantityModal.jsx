import { useState } from 'react'
import { useTranslation } from 'react-i18next'

function formatMacro(value) {
  return Math.round(Number(value) || 0)
}

export default function ServingQuantityModal({ food, mealType, onBack, onClose, onSubmit }) {
  const { t } = useTranslation()
  const [quantity, setQuantity] = useState('1')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const qty = Number(quantity) || 0
  const previewCalories = qty * Number(food?.calories ?? 0)
  const previewProtein = qty * Number(food?.protein ?? 0)
  const mealLabel = t(`meals.${mealType}`)
  const foodLabel = food.brand ? `${food.name} · ${food.brand}` : food.name

  async function handleSubmit(event) {
    event.preventDefault()
    if (!food?.id || qty <= 0) return

    setSubmitting(true)
    setError(null)
    try {
      await onSubmit({
        foodItemId: food.id,
        quantity: qty,
        mealType,
      })
    } catch (err) {
      setError(err.response?.data?.detail ?? t('food.addFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-slate-900/50 p-4 sm:items-center">
      <div
        className="w-full max-w-md rounded-2xl bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="serving-quantity-title"
      >
        <div className="border-b border-slate-100 px-5 py-4">
          <button
            type="button"
            onClick={onBack ?? onClose}
            className="mb-2 text-xs font-medium text-slate-500 hover:text-slate-700"
          >
            {t('food.backToSearch')}
          </button>
          <h2 id="serving-quantity-title" className="text-lg font-semibold text-slate-900">
            {t('food.howMuch')}
          </h2>
          <p className="text-sm text-slate-500">
            {t('food.addingTo', { meal: mealLabel, name: foodLabel })}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
            <p>
              {t('food.perServing', {
                size: food.serving_size,
                unit: food.serving_unit,
                calories: food.calories,
                protein: food.protein,
                carbs: food.carbs,
                fats: food.fats,
              })}
            </p>
          </div>

          <div>
            <label htmlFor="serving-quantity" className="mb-1 block text-sm font-medium text-slate-700">
              {t('food.quantityServings')}
            </label>
            <input
              id="serving-quantity"
              type="number"
              min="0.01"
              step="0.25"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none ring-emerald-500 focus:ring-2"
            />
            <p className="mt-2 text-xs text-slate-500">
              {t('food.preview', {
                calories: formatMacro(previewCalories),
                protein: formatMacro(previewProtein),
              })}
            </p>
          </div>

          {error ? <p className="text-sm text-rose-600">{error}</p> : null}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {t('food.cancel')}
            </button>
            <button
              type="submit"
              disabled={submitting || qty <= 0}
              className="flex-1 rounded-xl bg-emerald-600 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {submitting ? t('food.adding') : t('food.addToDiary')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
