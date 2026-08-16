import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function formatLabel(dateStr, isAr) {
  if (!dateStr || dateStr === 'start' || dateStr === 'now') return dateStr
  const d = new Date(`${dateStr}T12:00:00`)
  return d.toLocaleDateString(isAr ? 'ar-IQ' : 'en-GB', {
    month: 'short',
    day: 'numeric',
  })
}

function buildPoints(logs, progress, isAr, t) {
  const start = progress?.starting_weight_kg
  const current = progress?.current_weight_kg
  const sorted = [...(logs || [])].sort(
    (a, b) => new Date(a.recorded_at) - new Date(b.recorded_at),
  )

  let points = sorted.map((log) => ({
    key: log.id ?? log.recorded_at,
    date: log.recorded_at,
    label: formatLabel(log.recorded_at, isAr),
    weight: Number(log.weight_kg),
  }))

  if (start != null && points.length === 0 && current != null) {
    return [
      {
        key: 'start',
        date: 'start',
        label: t('weight.start'),
        weight: Number(start),
      },
      {
        key: 'now',
        date: 'now',
        label: t('weight.current'),
        weight: Number(current),
      },
    ]
  }

  if (start != null && points.length > 0) {
    const first = points[0]
    if (Math.abs(first.weight - Number(start)) > 0.05) {
      points.unshift({
        key: 'start',
        date: 'start',
        label: t('weight.start'),
        weight: Number(start),
      })
    }
  }

  if (current != null && points.length > 0) {
    const last = points[points.length - 1]
    if (Math.abs(last.weight - Number(current)) > 0.05) {
      points.push({
        key: 'now',
        date: 'now',
        label: t('weight.current'),
        weight: Number(current),
      })
    }
  }

  return points.map((p) =>
    p.date === 'start' || p.date === 'now'
      ? p
      : { ...p, label: p.label || formatLabel(p.date, isAr) },
  )
}

function WeightTooltip({ active, payload, t }) {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-lg border border-sky-200 bg-white px-3 py-2 text-sm shadow-md">
      <p className="font-medium text-sky-900">{item.label}</p>
      <p className="text-orange-600 font-semibold">
        {item.weight} {t('weight.kg')}
      </p>
    </div>
  )
}

export default function WeightLossChart({ logs, progress }) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')

  const points = useMemo(
    () => buildPoints(logs, progress, isAr, t),
    [logs, progress, isAr, t],
  )

  const lost = progress?.lost_kg ?? 0
  const hasTrend = points.length >= 2

  return (
    <div className="flex h-full min-h-[200px] flex-col rounded-xl border border-sky-100 bg-gradient-to-br from-sky-50 to-orange-50/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">
          {t('weight.chartTitle')}
        </p>
        {lost > 0 ? (
          <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-bold text-orange-700">
            −{lost} {t('weight.kg')}
          </span>
        ) : null}
      </div>

      {hasTrend ? (
        <div className="min-h-0 flex-1 w-full">
          <ResponsiveContainer width="100%" height={168}>
            <LineChart data={points} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#bae6fd" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: '#0369a1', fontSize: 11 }}
                axisLine={{ stroke: '#7dd3fc' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['dataMin - 1', 'dataMax + 0.5']}
                tick={{ fill: '#0369a1', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={36}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip content={<WeightTooltip t={t} />} />
              <Line
                type="monotone"
                dataKey="weight"
                stroke="#0284c7"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#f97316', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 6, fill: '#ea580c' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center px-2 text-center text-xs text-sky-600/80">
          {t('weight.chartHint')}
        </div>
      )}
    </div>
  )
}
