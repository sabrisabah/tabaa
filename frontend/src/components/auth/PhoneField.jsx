import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { authInputClass } from './AuthShell'
import { formatIraqLocalInput } from '../../utils/phone'

export default function PhoneField({
  id,
  label,
  value,
  onChange,
  autoFocus = false,
}) {
  const { t } = useTranslation()
  const generatedId = useId()
  const fieldId = id ?? generatedId

  return (
    <div className="space-y-2">
      <label htmlFor={fieldId} className="block text-sm font-medium text-slate-700">
        {label ?? t('auth.phone')}
      </label>
      <input
        id={fieldId}
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        autoFocus={autoFocus}
        value={value}
        onChange={(e) => onChange(formatIraqLocalInput(e.target.value))}
        required
        maxLength={11}
        placeholder="07XXXXXXXXX"
        className={authInputClass}
      />
      <p className="text-xs text-slate-500">{t('auth.phoneHint')}</p>
    </div>
  )
}
