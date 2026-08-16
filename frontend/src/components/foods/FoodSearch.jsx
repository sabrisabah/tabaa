import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { searchFoods } from '../../api/foods'

export default function FoodSearch({ onSelectFood }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [source, setSource] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const trimmed = query.trim()

    if (trimmed.length < 2) {
      setResults([])
      setSource(null)
      setError(null)
      setLoading(false)
      return undefined
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    const timer = setTimeout(async () => {
      try {
        const data = await searchFoods(trimmed)
        if (!cancelled) {
          setResults(data.results)
          setSource(data.source)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail ?? t('food.searchFailed'))
          setResults([])
          setSource(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 350)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, t])

  const sourceLabel =
    source === 'local'
      ? t('food.fromLocal')
      : source === 'openfoodfacts'
        ? t('food.fromOff')
        : source

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="food-search" className="mb-1 block text-sm font-medium text-slate-700">
          {t('food.searchLabel')}
        </label>
        <input
          id="food-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('food.searchPlaceholder')}
          autoFocus
          className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none ring-emerald-500 focus:ring-2"
        />
        <p className="mt-1 text-xs text-slate-400">{t('food.searchHint')}</p>
      </div>

      {source ? (
        <p className="text-xs font-medium text-slate-500">{sourceLabel}</p>
      ) : null}

      <div className="max-h-56 overflow-y-auto rounded-xl border border-slate-100">
        {loading ? (
          <p className="p-4 text-sm text-slate-500">{t('food.searching')}</p>
        ) : error ? (
          <p className="p-4 text-sm text-rose-600">{error}</p>
        ) : query.trim().length < 2 ? (
          <p className="p-4 text-sm text-slate-400">{t('food.startTyping')}</p>
        ) : results.length === 0 ? (
          <p className="p-4 text-sm text-slate-500">
            {t('food.noFoodsFor', { query: query.trim() })}
          </p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {results.map((food) => (
              <li key={food.id ?? food.barcode ?? food.name}>
                <button
                  type="button"
                  onClick={() => onSelectFood(food)}
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-start text-sm transition hover:bg-emerald-50"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-slate-800">{food.name}</span>
                    {food.brand ? (
                      <span className="block truncate text-xs text-slate-500">{food.brand}</span>
                    ) : null}
                    <span className="mt-0.5 block text-xs text-slate-400">
                      {food.serving_size}
                      {food.serving_unit}
                    </span>
                  </span>
                  <span className="shrink-0 text-sm font-semibold text-emerald-700">
                    {food.calories} kcal
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
