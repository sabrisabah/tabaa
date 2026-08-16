import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  createCardPayment,
  fetchCardPaymentStatus,
  fetchSavedCards,
} from '../../api/payments'

/**
 * Card checkout: amount is fixed from the selected subscription plan (no calculator).
 */
export default function CardPayCalculator({
  amountIqd = 25000,
  planLabel = '',
  subscriptionId = null,
  onBeforePay,
  onPaid,
}) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const amount = Number(amountIqd) || 0
  const [savedCards, setSavedCards] = useState([])
  const [method, setMethod] = useState('new')
  const [cardNumber, setCardNumber] = useState('')
  const [expMonth, setExpMonth] = useState('')
  const [expYear, setExpYear] = useState('')
  const [cvv, setCvv] = useState('')
  const [name, setName] = useState('')
  const [saveCard, setSaveCard] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  useEffect(() => {
    fetchSavedCards()
      .then((list) => {
        setSavedCards(list)
        if (list[0]) setMethod(String(list[0].id))
      })
      .catch(() => setSavedCards([]))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const order = params.get('order')
    const payment = params.get('payment')
    if (!order) return
    fetchCardPaymentStatus(order)
      .then((p) => {
        if (p.status === 'succeeded' || payment === 'success') {
          setInfo(t('cardPay.success', { tx: p.gateway_transaction_id }))
          onPaid?.(p)
        } else if (p.status === 'failed' || payment === 'failed') {
          setError(p.failure_reason || t('cardPay.failed'))
        }
      })
      .catch(() => {})
  }, [onPaid, t])

  async function handlePay() {
    if (!amount || amount < 1000) {
      setError(t('cardPay.amountInvalid'))
      return
    }
    setBusy(true)
    setError('')
    setInfo('')
    try {
      let subId = subscriptionId
      let chargeAmount = amount
      if (onBeforePay) {
        const ensured = await onBeforePay()
        if (ensured?.id) subId = ensured.id
        if (ensured?.amount_iqd) chargeAmount = Number(ensured.amount_iqd)
      }
      const payload = {
        amount_iqd: chargeAmount,
        subscription_id: subId || undefined,
        save_card: saveCard,
      }
      if (method === 'new') {
        payload.card_number = cardNumber.replace(/\s+/g, '')
        payload.card_exp_month = Number(expMonth)
        payload.card_exp_year = Number(expYear)
        payload.card_cvv = cvv
        payload.cardholder_name = name
      } else {
        payload.saved_method_id = Number(method)
      }
      const data = await createCardPayment(payload)
      setCardNumber('')
      setCvv('')
      setInfo(t('cardPay.redirecting'))
      if (data.redirect_url) {
        window.location.href = data.redirect_url
      }
    } catch (err) {
      setError(err?.response?.data?.detail || t('cardPay.payError'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 p-4" dir={isAr ? 'rtl' : 'ltr'}>
      <div>
        <p className="text-sm font-semibold text-slate-900">{t('cardPay.title')}</p>
        <p className="mt-1 text-xs text-slate-500">{t('cardPay.pciNote')}</p>
      </div>

      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-center">
        <p className="text-xs font-semibold text-emerald-800">{t('cardPay.planAmount')}</p>
        {planLabel ? (
          <p className="mt-1 text-sm text-slate-700">{planLabel}</p>
        ) : null}
        <p className="mt-1 font-mono text-2xl font-bold text-slate-900">
          {amount.toLocaleString()} <span className="text-base font-semibold">د.ع</span>
        </p>
        <p className="mt-1 text-xs text-slate-500">{t('cardPay.amountFixed')}</p>
      </div>

      {savedCards.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-600">{t('cardPay.savedCards')}</p>
          {savedCards.map((card) => (
            <label
              key={card.id}
              className={`flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2 text-sm ${
                method === String(card.id)
                  ? 'border-emerald-500 bg-emerald-50'
                  : 'border-slate-200'
              }`}
            >
              <input
                type="radio"
                name="card-method"
                checked={method === String(card.id)}
                onChange={() => setMethod(String(card.id))}
              />
              <span className="font-medium capitalize">{card.brand || 'card'}</span>
              <span className="font-mono" dir="ltr">
                •••• {card.last4}
              </span>
            </label>
          ))}
          <label
            className={`flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2 text-sm ${
              method === 'new' ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200'
            }`}
          >
            <input
              type="radio"
              name="card-method"
              checked={method === 'new'}
              onChange={() => setMethod('new')}
            />
            {t('cardPay.newCard')}
          </label>
        </div>
      ) : null}

      {method === 'new' || savedCards.length === 0 ? (
        <div className="space-y-2">
          <input
            value={cardNumber}
            onChange={(e) => setCardNumber(e.target.value)}
            placeholder={t('cardPay.cardNumber')}
            inputMode="numeric"
            autoComplete="cc-number"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            dir="ltr"
          />
          <div className="grid grid-cols-3 gap-2">
            <input
              value={expMonth}
              onChange={(e) => setExpMonth(e.target.value)}
              placeholder="MM"
              inputMode="numeric"
              autoComplete="cc-exp-month"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              dir="ltr"
            />
            <input
              value={expYear}
              onChange={(e) => setExpYear(e.target.value)}
              placeholder="YYYY"
              inputMode="numeric"
              autoComplete="cc-exp-year"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              dir="ltr"
            />
            <input
              value={cvv}
              onChange={(e) => setCvv(e.target.value)}
              placeholder="CVV"
              inputMode="numeric"
              autoComplete="cc-csc"
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              dir="ltr"
            />
          </div>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('cardPay.cardName')}
            autoComplete="cc-name"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
          />
          <label className="flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={saveCard}
              onChange={(e) => setSaveCard(e.target.checked)}
            />
            {t('cardPay.saveTokenOnly')}
          </label>
        </div>
      ) : null}

      <button
        type="button"
        disabled={busy || !amount}
        onClick={handlePay}
        className="w-full rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
      >
        {busy ? t('common.loading') : t('cardPay.pay')}
      </button>

      {info ? <p className="text-sm text-emerald-700">{info}</p> : null}
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
    </div>
  )
}
