import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ageFromBirthday,
  daysInMonth,
} from '../../utils/profileUnits'
import GlassSelect from './GlassSelect'

const styles = {
  solid: {
    shell: 'overflow-hidden rounded-2xl border border-slate-200 bg-white',
    header: 'border-b border-slate-100 px-4 py-3 text-center',
    title: 'text-base font-semibold text-slate-900',
    row: 'grid grid-cols-1 items-start gap-3 border-b border-slate-100 py-4 last:border-b-0 sm:grid-cols-[140px_1fr]',
    label: 'flex items-center gap-1.5 pt-2 text-sm font-medium text-slate-800',
    help: 'inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 text-[10px] font-semibold text-slate-400',
    option: 'flex cursor-pointer items-center gap-2 text-sm text-slate-800',
    radioOn: 'border-violet-600',
    radioOff: 'border-slate-300',
    radioDotOn: 'bg-violet-600',
    fieldLabel: 'block text-xs text-slate-500',
    input:
      'w-full rounded-full border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20',
  },
  glass: {
    shell:
      'overflow-visible rounded-[1.5rem] border border-white/30 bg-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-md',
    header: 'border-b border-white/20 px-4 py-3 text-center',
    title: 'text-base font-semibold text-white',
    row: 'relative z-10 grid grid-cols-1 items-start gap-3 border-b border-white/15 py-4 last:z-30 last:border-b-0 sm:grid-cols-[140px_1fr]',
    label: 'flex items-center gap-1.5 pt-2 text-sm font-medium text-white',
    help: 'inline-flex h-4 w-4 items-center justify-center rounded-full border border-white/50 text-[10px] font-semibold text-white/80',
    option: 'flex cursor-pointer items-center gap-2 text-sm text-white',
    radioOn: 'border-white',
    radioOff: 'border-white/50',
    radioDotOn: 'bg-white',
    fieldLabel: 'block text-xs text-white/70',
    input:
      'w-full rounded-full border border-white/60 bg-white/10 px-3 py-2 text-sm text-white outline-none backdrop-blur-sm placeholder:text-white/50 focus:border-white focus:ring-2 focus:ring-white/20',
  },
}

function HelpIcon({ title, className }) {
  return (
    <span className={className} title={title}>
      ?
    </span>
  )
}

function Row({ label, hint, hintTitle, children, s }) {
  return (
    <div className={s.row}>
      <div className={s.label}>
        <span>{label}</span>
        {hint ? <HelpIcon title={hintTitle} className={s.help} /> : null}
      </div>
      <div>{children}</div>
    </div>
  )
}

export const defaultProfileDetails = () => {
  const now = new Date()
  return {
    gender: 'male',
    birthDay: 1,
    birthMonth: 0,
    birthYear: now.getFullYear() - 25,
    heightCm: '170',
    weightValue: '70',
    weightUnit: 'kg',
    activity_level: 'moderately_active',
  }
}

export function profileDetailsToPayload(details) {
  const age = ageFromBirthday(
    Number(details.birthYear),
    Number(details.birthMonth),
    Number(details.birthDay),
  )
  const height_cm = Number(details.heightCm)
  const weight_kg = Number(details.weightValue)

  return {
    gender: details.gender,
    age,
    height_cm,
    weight_kg,
    activity_level: details.activity_level || 'moderately_active',
  }
}

export function isProfileDetailsValid(details) {
  const payload = profileDetailsToPayload(details)
  return (
    (payload.gender === 'male' || payload.gender === 'female') &&
    payload.age != null &&
    payload.age >= 13 &&
    payload.age <= 120 &&
    payload.height_cm >= 50 &&
    payload.height_cm <= 300 &&
    payload.weight_kg >= 1 &&
    payload.weight_kg <= 500
  )
}

export default function ProfileDetailsFields({ value, onChange, variant = 'solid' }) {
  const { t } = useTranslation()
  const s = styles[variant] || styles.solid
  const glass = variant === 'glass'
  const months = t('profile.months', { returnObjects: true })

  const years = useMemo(() => {
    const current = new Date().getFullYear()
    return Array.from({ length: 100 }, (_, i) => current - 13 - i)
  }, [])

  const maxDay = daysInMonth(Number(value.birthYear), Number(value.birthMonth))
  const activityHelp = t('profile.activityHelp')

  const dayOptions = useMemo(
    () => Array.from({ length: maxDay }, (_, i) => ({ value: i + 1, label: String(i + 1) })),
    [maxDay],
  )
  const monthOptions = useMemo(
    () =>
      (Array.isArray(months) ? months : []).map((month, index) => ({
        value: index,
        label: month,
      })),
    [months],
  )
  const yearOptions = useMemo(
    () => years.map((year) => ({ value: year, label: String(year) })),
    [years],
  )
  const activityOptions = useMemo(
    () => [
      { value: 'sedentary', label: t('profile.sedentary') },
      { value: 'lightly_active', label: t('profile.lightlyActive') },
      { value: 'moderately_active', label: t('profile.moderatelyActive') },
      { value: 'very_active', label: t('profile.veryActive') },
      { value: 'extra_active', label: t('profile.extraActive') },
    ],
    [t],
  )

  function patch(partial) {
    onChange({ ...value, ...partial })
  }

  function setBirthday({ birthDay, birthMonth, birthYear }) {
    const nextYear = birthYear ?? value.birthYear
    const nextMonth = birthMonth ?? value.birthMonth
    const nextMax = daysInMonth(Number(nextYear), Number(nextMonth))
    const nextDay = Math.min(Number(birthDay ?? value.birthDay), nextMax)
    patch({ birthDay: nextDay, birthMonth: nextMonth, birthYear: nextYear })
  }

  return (
    <div className={s.shell}>
      {variant === 'solid' ? (
        <div className={s.header}>
          <h2 className={s.title}>{t('profile.title')}</h2>
        </div>
      ) : null}

      <div className="px-4">
        <Row label={t('profile.sex')} hint hintTitle={activityHelp} s={s}>
          <div className="flex flex-wrap gap-5 pt-1">
            {[
              { value: 'male', label: t('profile.male') },
              { value: 'female', label: t('profile.female') },
            ].map((option) => {
              const selected = value.gender === option.value
              return (
                <label key={option.value} className={s.option}>
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full border-2 ${
                      selected ? s.radioOn : s.radioOff
                    }`}
                  >
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        selected ? s.radioDotOn : 'bg-transparent'
                      }`}
                    />
                  </span>
                  <input
                    type="radio"
                    name="sex"
                    value={option.value}
                    checked={selected}
                    onChange={() => patch({ gender: option.value })}
                    className="sr-only"
                  />
                  {option.label}
                </label>
              )
            })}
          </div>
        </Row>

        <Row label={t('profile.birthday')} s={s}>
          <div className="flex flex-wrap items-end gap-2">
            <label className="space-y-1">
              <span className={s.fieldLabel}>{t('profile.day')}</span>
              {glass ? (
                <GlassSelect
                  value={value.birthDay}
                  options={dayOptions}
                  onChange={(day) => setBirthday({ birthDay: Number(day) })}
                />
              ) : (
                <select
                  className={s.input}
                  value={value.birthDay}
                  onChange={(e) => setBirthday({ birthDay: Number(e.target.value) })}
                >
                  {dayOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
            </label>
            <label className="space-y-1">
              <span className={s.fieldLabel}>{t('profile.month')}</span>
              {glass ? (
                <GlassSelect
                  className="min-w-[8rem]"
                  value={value.birthMonth}
                  options={monthOptions}
                  onChange={(month) => setBirthday({ birthMonth: Number(month) })}
                />
              ) : (
                <select
                  className={s.input}
                  value={value.birthMonth}
                  onChange={(e) => setBirthday({ birthMonth: Number(e.target.value) })}
                >
                  {monthOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
            </label>
            <label className="space-y-1">
              <span className={s.fieldLabel}>{t('profile.year')}</span>
              {glass ? (
                <GlassSelect
                  value={value.birthYear}
                  options={yearOptions}
                  onChange={(year) => setBirthday({ birthYear: Number(year) })}
                />
              ) : (
                <select
                  className={s.input}
                  value={value.birthYear}
                  onChange={(e) => setBirthday({ birthYear: Number(e.target.value) })}
                >
                  {yearOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}
            </label>
          </div>
        </Row>

        <Row label={t('profile.height')} s={s}>
          <div className="flex flex-wrap items-end gap-2">
            <label className="space-y-1">
              <span className={s.fieldLabel}>{t('profile.cm')}</span>
              <input
                type="number"
                min="50"
                max="300"
                step="0.1"
                value={value.heightCm}
                onChange={(e) => patch({ heightCm: e.target.value })}
                className={`${s.input} w-32`}
              />
            </label>
          </div>
        </Row>

        <Row label={t('profile.weight')} s={s}>
          <div className="flex flex-wrap items-end gap-2">
            <label className="space-y-1">
              <span className={s.fieldLabel}>{t('profile.kg')}</span>
              <input
                type="number"
                min="1"
                step="0.1"
                value={value.weightValue}
                onChange={(e) => patch({ weightValue: e.target.value, weightUnit: 'kg' })}
                className={`${s.input} w-32`}
              />
            </label>
          </div>
        </Row>

        <Row label={t('profile.activity')} hint hintTitle={activityHelp} s={s}>
          {glass ? (
            <GlassSelect
              className="w-full max-w-sm"
              value={value.activity_level}
              options={activityOptions}
              placement="top"
              onChange={(activity) => patch({ activity_level: activity })}
            />
          ) : (
            <select
              className={`${s.input} w-full max-w-sm`}
              value={value.activity_level}
              onChange={(e) => patch({ activity_level: e.target.value })}
            >
              {activityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}
        </Row>
      </div>
    </div>
  )
}
