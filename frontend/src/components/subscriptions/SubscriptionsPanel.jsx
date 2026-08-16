import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import CardPayCalculator from '../payments/CardPayCalculator'
import SubscriptionCalendar from './SubscriptionCalendar'
import {
  confirmTransfer,
  createSubscription,
  fetchSubscriptionPlans,
  fetchSubscriptionStatus,
} from '../../api/subscriptions'

const STATUS_KEYS = {
  pending_payment: 'pendingPayment',
  paid_pending_activation: 'paidPending',
  active: 'active',
  expired: 'expired',
  cancelled: 'cancelled',
}

export default function SubscriptionsPanel({ open, onClose, onAccessChange, onMealsUnlocked }) {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language?.startsWith('ar')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [plans, setPlans] = useState([])
  const [status, setStatus] = useState(null)
  const [paymentInfo, setPaymentInfo] = useState(null)
  const [selectedPlan, setSelectedPlan] = useState('monthly')
  const [fullName, setFullName] = useState('')
  const [address, setAddress] = useState('')
  const [gps, setGps] = useState({ lat: null, lng: null })
  const [gpsStatus, setGpsStatus] = useState('')
  const [payMode, setPayMode] = useState('card')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const [me, planList] = await Promise.all([
        fetchSubscriptionStatus(),
        fetchSubscriptionPlans(),
      ])
      setStatus(me)
      setPlans(planList)
      onAccessChange?.(Boolean(me.has_meal_access))
      if (me.weight_progress?.full_name) setFullName(me.weight_progress.full_name)
      if (me.latest?.plan?.code) {
        setSelectedPlan(me.latest.plan.code)
      } else if (planList.length && !planList.find((p) => p.code === selectedPlan)) {
        setSelectedPlan(planList[0].code)
      }
      if (me.latest && me.superqi) {
        setPaymentInfo({
          ...me.superqi,
          amount_iqd: me.latest.amount_iqd,
          payment_reference: me.latest.payment_reference,
        })
      }
      return me
    } catch (err) {
      setError(err?.response?.data?.detail || t('subscriptions.loadError'))
      return null
    } finally {
      setLoading(false)
    }
  }

  async function unlockMealsIfPaid(me) {
    if (me?.has_meal_access) {
      onAccessChange?.(true)
      onMealsUnlocked?.()
    }
  }

  useEffect(() => {
    if (open) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  function captureGps() {
    if (!navigator.geolocation) {
      setGpsStatus(t('subscriptions.gpsUnavailable'))
      return
    }
    setGpsStatus(t('subscriptions.gpsLoading'))
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({
          lat: Number(pos.coords.latitude.toFixed(6)),
          lng: Number(pos.coords.longitude.toFixed(6)),
        })
        setGpsStatus(t('subscriptions.gpsOk'))
      },
      () => setGpsStatus(t('subscriptions.gpsDenied')),
      { enableHighAccuracy: true, timeout: 12000 },
    )
  }

  async function handleSubscribe() {
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      const data = await createSubscription(selectedPlan)
      setPaymentInfo(data.superqi)
      await load()
      return data.subscription
    } catch (err) {
      const detail = err?.response?.data?.detail
      const existingSuperqi = err?.response?.data?.superqi
      const existing = err?.response?.data?.subscription
      if (existingSuperqi) setPaymentInfo(existingSuperqi)
      else if (existing) {
        setPaymentInfo({
          ...(status?.superqi || {}),
          amount_iqd: existing.amount_iqd,
          payment_reference: existing.payment_reference,
        })
      }
      // Switching pending plan now returns 200 from backend; keep error only for hard failures.
      if (existing && err?.response?.status === 400 && existing.status === 'pending_payment') {
        await load()
        return existing
      }
      setError(detail || t('subscriptions.subscribeError'))
      await load()
      return existing || null
    } finally {
      setSubmitting(false)
    }
  }

  async function handleConfirmTransfer() {
    if (!fullName.trim() || !address.trim()) {
      setError(t('subscriptions.nameAddressRequired'))
      return
    }
    setConfirming(true)
    setError('')
    setSuccess('')
    try {
      let lat = gps.lat
      let lng = gps.lng
      if (lat == null && navigator.geolocation) {
        const coords = await new Promise((resolve) => {
          navigator.geolocation.getCurrentPosition(
            (pos) =>
              resolve({
                lat: Number(pos.coords.latitude.toFixed(6)),
                lng: Number(pos.coords.longitude.toFixed(6)),
              }),
            () => resolve({ lat: null, lng: null }),
            { enableHighAccuracy: true, timeout: 8000 },
          )
        })
        lat = coords.lat
        lng = coords.lng
        if (lat != null) setGps(coords)
      }
      const data = await confirmTransfer({
        full_name: fullName.trim(),
        address: address.trim(),
        subscription_id: status?.latest?.id,
        gps_latitude: lat,
        gps_longitude: lng,
      })
      setSuccess(data.detail || t('subscriptions.confirmOk'))
      const me = await load()
      await unlockMealsIfPaid(me)
    } catch (err) {
      setError(err?.response?.data?.detail || t('subscriptions.confirmError'))
    } finally {
      setConfirming(false)
    }
  }

  if (!open) return null

  const latest = status?.latest
  const statusKey = latest ? STATUS_KEYS[latest.status] : null
  const superqi = paymentInfo || status?.superqi || {}
  const phone = superqi.merchant_phone_clean || superqi.merchant_phone || ''
  const instructions = isAr ? superqi.instructions_ar : superqi.instructions_en
  const canConfirm =
    latest &&
    (latest.status === 'pending_payment' || latest.status === 'paid_pending_activation')
  const selectedPlanObj = plans.find((p) => p.code === selectedPlan)
  // Always show the amount for the plan the user currently selected.
  const planAmount = selectedPlanObj?.price_iqd || latest?.amount_iqd || 25000
  const planLabel = selectedPlanObj
    ? isAr
      ? selectedPlanObj.name_ar
      : selectedPlanObj.name_en
    : latest?.plan
      ? isAr
        ? latest.plan.name_ar
        : latest.plan.name_en
      : ''

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-slate-900/40" onClick={onClose}>
      <aside
        className="flex h-full w-full max-w-md flex-col bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        dir={isAr ? 'rtl' : 'ltr'}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="text-lg font-bold text-slate-900">{t('subscriptions.title')}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
          >
            {t('common.close')}
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          {loading ? (
            <p className="text-sm text-slate-500">{t('common.loading')}</p>
          ) : (
            <>
              <p className="text-sm leading-relaxed text-slate-600">
                {t('subscriptions.introCard')}
              </p>

              <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => setPayMode('card')}
                  className={`rounded-lg px-3 py-2 text-sm font-semibold ${
                    payMode === 'card' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
                  }`}
                >
                  {t('cardPay.tab')}
                </button>
                <button
                  type="button"
                  onClick={() => setPayMode('transfer')}
                  className={`rounded-lg px-3 py-2 text-sm font-semibold ${
                    payMode === 'transfer' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
                  }`}
                >
                  {t('subscriptions.transferTab')}
                </button>
              </div>

              {status?.has_meal_access ? (
                <div className="space-y-4">
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                    {t('subscriptions.activeBanner')}
                    {latest?.ends_at ? (
                      <p className="mt-1 text-xs">
                        {t('subscriptions.endsAt')}:{' '}
                        {new Date(latest.ends_at).toLocaleDateString(isAr ? 'ar-IQ' : 'en')}
                      </p>
                    ) : null}
                  </div>
                  {status?.active?.starts_at && status?.active?.ends_at ? (
                    <SubscriptionCalendar
                      compact
                      startsAt={status.active.starts_at}
                      endsAt={status.active.ends_at}
                      accessActive
                      planName={
                        isAr ? status.active.plan?.name_ar : status.active.plan?.name_en
                      }
                    />
                  ) : status?.calendar?.starts_at ? (
                    <SubscriptionCalendar
                      compact
                      startsAt={status.calendar.starts_at}
                      endsAt={status.calendar.ends_at}
                      accessActive={Boolean(status.calendar.access_active)}
                      planName={
                        isAr ? status.calendar.plan_name_ar : status.calendar.plan_name_en
                      }
                    />
                  ) : null}
                </div>
              ) : null}

              {latest && !status?.has_meal_access ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-semibold">
                    {t(`subscriptions.status.${statusKey || 'pendingPayment'}`)}
                  </p>
                  <p className="mt-1 text-xs">
                    {t('subscriptions.reference')}:{' '}
                    <span className="font-mono font-bold">{latest.payment_reference}</span>
                  </p>
                  <p className="mt-1 text-xs">
                    {t('subscriptions.amount')}: {latest.amount_iqd?.toLocaleString()}{' '}
                    {t('subscriptions.iqd')}
                  </p>
                </div>
              ) : null}

              {!status?.has_meal_access ? (
                <div className="space-y-3">
                  <p className="text-sm font-semibold text-slate-800">
                    {t('subscriptions.choosePlan')}
                  </p>
                  {plans.map((plan) => {
                    const selected = selectedPlan === plan.code
                    return (
                      <button
                        key={plan.id}
                        type="button"
                        onClick={() => setSelectedPlan(plan.code)}
                        className={`w-full rounded-xl border px-4 py-3 text-start transition ${
                          selected
                            ? 'border-emerald-500 bg-emerald-50'
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <p className="font-semibold text-slate-900">
                          {isAr ? plan.name_ar : plan.name_en}
                        </p>
                        <p className="text-sm text-slate-600">
                          {plan.price_iqd.toLocaleString()} {t('subscriptions.iqd')} ·{' '}
                          {plan.duration_days} {t('subscriptions.days')}
                        </p>
                        {plan.meal_variety_level > 1 ? (
                          <p className="mt-1 text-xs text-emerald-700">
                            {t('subscriptions.moreVariety')}
                          </p>
                        ) : null}
                      </button>
                    )
                  })}
                  <button
                    type="button"
                    disabled={submitting || latest?.status === 'paid_pending_activation'}
                    onClick={handleSubscribe}
                    className="w-full rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
                  >
                    {submitting ? t('common.loading') : t('subscriptions.prepareOrder')}
                  </button>
                </div>
              ) : null}

              {payMode === 'card' && !status?.has_meal_access ? (
                <CardPayCalculator
                  amountIqd={planAmount}
                  planLabel={planLabel}
                  subscriptionId={
                    latest?.plan?.code === selectedPlan ? latest?.id : null
                  }
                  onBeforePay={async () => {
                    const sub = await handleSubscribe()
                    return sub
                  }}
                  onPaid={async () => {
                    const me = await load()
                    setSuccess(t('cardPay.successShort'))
                    await unlockMealsIfPaid(me)
                  }}
                />
              ) : null}

              {payMode === 'transfer' && !status?.has_meal_access ? (
                <>
                  {phone ? (
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                      <p className="text-xs font-semibold text-emerald-800">
                        {isAr
                          ? superqi.title_ar || t('subscriptions.superQiNumber')
                          : superqi.title_en || t('subscriptions.superQiNumber')}
                      </p>
                      <p
                        className="mt-1 font-mono text-2xl font-bold tracking-wide text-slate-900"
                        dir="ltr"
                      >
                        {phone}
                      </p>
                      <p className="mt-1 text-xs text-emerald-700">
                        {isAr
                          ? superqi.hint_ar || t('subscriptions.transferDirect')
                          : superqi.hint_en || t('subscriptions.transferDirect')}
                      </p>
                    </div>
                  ) : null}

                  {instructions ? (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                      <p className="font-semibold text-slate-900">{t('subscriptions.howToPay')}</p>
                      <p className="mt-2 leading-relaxed">{instructions}</p>
                      {(superqi.payment_reference || latest?.payment_reference) && (
                        <p className="mt-3 rounded-lg bg-white px-3 py-2 font-mono text-base font-bold text-slate-900">
                          {superqi.payment_reference || latest?.payment_reference}
                        </p>
                      )}
                    </div>
                  ) : null}

                  {canConfirm ? (
                    <div className="space-y-3 rounded-xl border border-slate-200 p-4">
                      <p className="text-sm font-semibold text-slate-900">
                        {t('subscriptions.confirmTitle')}
                      </p>
                      <label className="block text-sm">
                        <span className="text-slate-600">{t('subscriptions.fullName')}</span>
                        <input
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                        />
                      </label>
                      <label className="block text-sm">
                        <span className="text-slate-600">{t('subscriptions.address')}</span>
                        <input
                          value={address}
                          onChange={(e) => setAddress(e.target.value)}
                          className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                        />
                      </label>
                      <button
                        type="button"
                        onClick={captureGps}
                        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                      >
                        {t('subscriptions.captureGps')}
                      </button>
                      {gpsStatus ? <p className="text-xs text-slate-500">{gpsStatus}</p> : null}
                      {gps.lat != null ? (
                        <p className="font-mono text-xs text-slate-500" dir="ltr">
                          {gps.lat}, {gps.lng}
                        </p>
                      ) : null}
                      <button
                        type="button"
                        disabled={confirming}
                        onClick={handleConfirmTransfer}
                        className="w-full rounded-xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
                      >
                        {confirming ? t('common.loading') : t('subscriptions.confirmTransfer')}
                      </button>
                    </div>
                  ) : null}
                </>
              ) : null}

              {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
              {error ? <p className="text-sm text-rose-600">{error}</p> : null}
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
