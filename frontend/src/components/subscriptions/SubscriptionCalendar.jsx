import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

function startOfDay(d) {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x
}

function addDays(d, n) {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}

function sameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function daysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate()
}

/**
 * Subscription period calendar.
 * Finished days turn white (no active subscription on those days).
 */
export default function SubscriptionCalendar({
  startsAt,
  endsAt,
  planName = '',
  compact = false,
  accessActive = true,
  onRenew,
}) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const locale = isAr ? 'ar-IQ' : 'en-GB'

  const start = useMemo(() => (startsAt ? startOfDay(new Date(startsAt)) : null), [startsAt])
  const end = useMemo(() => (endsAt ? startOfDay(new Date(endsAt)) : null), [endsAt])
  const today = useMemo(() => startOfDay(new Date()), [])
  const fullyExpired = !accessActive || (end && today > end)

  const initialMonth = start || today
  const [viewYear, setViewYear] = useState(initialMonth.getFullYear())
  const [viewMonth, setViewMonth] = useState(initialMonth.getMonth())

  const stats = useMemo(() => {
    if (!start || !end) return null
    const total = Math.max(1, Math.round((end - start) / 86400000) + 1)
    let elapsed = Math.round((today - start) / 86400000) + 1
    if (today < start) elapsed = 0
    if (today > end) elapsed = total
    const remaining = fullyExpired ? 0 : Math.max(0, total - elapsed)
    const pct = Math.min(100, Math.round((elapsed / total) * 100))
    return { total, elapsed, remaining, pct }
  }, [start, end, today, fullyExpired])

  const weekdays = useMemo(() => {
    const base = new Date(2024, 5, 1)
    return Array.from({ length: 7 }, (_, i) =>
      addDays(base, i).toLocaleDateString(locale, { weekday: 'short' }),
    )
  }, [locale])

  const cells = useMemo(() => {
    const first = new Date(viewYear, viewMonth, 1)
    const jsDay = first.getDay()
    const offset = (jsDay + 1) % 7
    const totalDays = daysInMonth(viewYear, viewMonth)
    const list = []
    for (let i = 0; i < offset; i += 1) list.push(null)
    for (let d = 1; d <= totalDays; d += 1) {
      list.push(new Date(viewYear, viewMonth, d))
    }
    while (list.length % 7 !== 0) list.push(null)
    return list
  }, [viewYear, viewMonth])

  function prevMonth() {
    if (viewMonth === 0) {
      setViewMonth(11)
      setViewYear((y) => y - 1)
    } else setViewMonth((m) => m - 1)
  }

  function nextMonth() {
    if (viewMonth === 11) {
      setViewMonth(0)
      setViewYear((y) => y + 1)
    } else setViewMonth((m) => m + 1)
  }

  if (!start || !end) return null

  const monthTitle = new Date(viewYear, viewMonth, 1).toLocaleDateString(locale, {
    month: 'long',
    year: 'numeric',
  })

  const endLabel = end.toLocaleDateString(locale)

  return (
    <section
      className={`overflow-hidden rounded-2xl border bg-white shadow-md ${
        fullyExpired ? 'border-rose-200' : 'border-sky-200'
      } ${compact ? 'p-3' : 'p-4'}`}
      dir={isAr ? 'rtl' : 'ltr'}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p
            className={`text-xs font-semibold uppercase tracking-wider ${
              fullyExpired ? 'text-rose-600' : 'text-sky-700'
            }`}
          >
            {fullyExpired ? t('calendar.expiredBadge') : t('calendar.badge')}
          </p>
          <h3 className={`font-bold text-slate-900 ${compact ? 'text-sm' : 'text-base'}`}>
            {t('calendar.title')}
          </h3>
          {planName ? <p className="mt-0.5 text-xs text-slate-500">{planName}</p> : null}
        </div>
        <div className="rounded-lg bg-gradient-to-br from-sky-50 to-orange-50 px-2 py-1 text-center">
          <p className="text-[10px] text-slate-500">{t('calendar.remaining')}</p>
          <p className="text-sm font-bold text-slate-900">
            {stats?.remaining ?? 0} {t('calendar.days')}
          </p>
        </div>
      </div>

      {fullyExpired ? (
        <div className="mb-3 rounded-xl border border-rose-100 bg-rose-50 px-3 py-2 text-xs leading-relaxed text-rose-800">
          {t('calendar.expiredHint', { date: endLabel })}
          {onRenew ? (
            <button
              type="button"
              onClick={onRenew}
              className="mt-2 w-full rounded-lg bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-500"
            >
              {t('calendar.renewCta')}
            </button>
          ) : null}
        </div>
      ) : null}

      {stats && !fullyExpired ? (
        <div className="mb-3">
          <div className="mb-1 flex justify-between text-[11px] text-slate-500">
            <span>
              {t('calendar.dayOf', {
                current: Math.min(stats.elapsed, stats.total),
                total: stats.total,
              })}
            </span>
            <span>{stats.pct}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-gradient-to-l from-orange-400 to-sky-500 transition-all"
              style={{ width: `${stats.pct}%` }}
            />
          </div>
        </div>
      ) : null}

      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={prevMonth}
          className="rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
        >
          {isAr ? '→' : '←'}
        </button>
        <p className="text-sm font-semibold text-slate-800">{monthTitle}</p>
        <button
          type="button"
          onClick={nextMonth}
          className="rounded-lg px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
        >
          {isAr ? '←' : '→'}
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-medium text-slate-400">
        {weekdays.map((w) => (
          <div key={w} className="py-1">
            {w}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, idx) => {
          if (!day) return <div key={`e-${idx}`} className="aspect-square" />
          const inRange = day >= start && day <= end
          const isToday = sameDay(day, today)
          const finished = inRange && (day < today || fullyExpired)
          const isFuture = inRange && day > today && !fullyExpired
          let cls =
            'aspect-square rounded-lg text-xs font-medium flex items-center justify-center transition '
          if (finished) {
            // Finished / no-subscription look (white)
            cls += 'bg-white text-slate-300 border border-slate-100'
          } else if (inRange && isToday && !fullyExpired) {
            cls += 'bg-gradient-to-br from-orange-500 to-sky-600 text-white shadow-sm ring-2 ring-orange-200'
          } else if (isFuture) {
            cls += 'bg-sky-800 text-white'
          } else {
            cls += 'text-slate-300'
          }
          return (
            <div key={day.toISOString()} className={cls} title={day.toLocaleDateString(locale)}>
              {day.getDate()}
            </div>
          )
        })}
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-slate-500">
        <span className="inline-flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded bg-gradient-to-br from-orange-500 to-sky-600" />{' '}
          {t('calendar.today')}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded border border-slate-200 bg-white" />{' '}
          {t('calendar.finished')}
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded bg-sky-800" /> {t('calendar.upcoming')}
        </span>
      </div>

      <p className="mt-3 border-t border-slate-100 pt-2 text-[11px] text-slate-500">
        {t('calendar.period', {
          from: start.toLocaleDateString(locale),
          to: end.toLocaleDateString(locale),
        })}
      </p>
    </section>
  )
}
