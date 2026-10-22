import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'
import GlassSelect from '../components/auth/GlassSelect'
import TdeeCalculator from '../components/tdee/TdeeCalculator'
import { clinicApi, formatIqd, nutritionPlansApi } from '../api/clinic'
import { fetchMyProfile } from '../api/profile'
import {
  glassAlertErr,
  glassAlertOk,
  glassAlertWarn,
  glassBtnDanger,
  glassBtnGhost,
  glassBtnWhite,
  glassField,
  glassHeader,
  glassPageBg,
  glassPanel,
  glassStat,
  glassTabActive,
  glassTabIdle,
} from '../styles/glassTheme'

const DISCOUNT_REASONS = [
  { value: 'friends', label: 'الأصدقاء' },
  { value: 'relatives', label: 'الأقارب' },
  { value: 'students', label: 'الطلبة' },
  { value: 'disability', label: 'ذوو الإعاقة' },
  { value: 'custom', label: 'سبب مخصص' },
]

const ACTIVITY_OPTIONS = [
  { value: 'sedentary', label: 'قليل الحركة' },
  { value: 'lightly_active', label: 'نشاط خفيف' },
  { value: 'moderately_active', label: 'نشاط متوسط' },
  { value: 'very_active', label: 'نشاط عالٍ' },
  { value: 'extra_active', label: 'نشاط مكثف' },
]

function clinicErrorMessage(err, fallback = 'تعذر تنفيذ الطلب') {
  const data = err?.response?.data
  if (!data) return err?.message || fallback
  if (typeof data === 'string') return data
  if (typeof data.detail === 'string') return data.detail
  const parts = []
  for (const value of Object.values(data)) {
    if (Array.isArray(value)) parts.push(...value.map(String))
    else if (value && typeof value === 'object') parts.push(JSON.stringify(value))
    else if (value != null) parts.push(String(value))
  }
  return parts.filter(Boolean).join(' ') || fallback
}

function TabButton({ active, onClick, children }) {
  return (
    <button type="button" onClick={onClick} className={active ? glassTabActive : glassTabIdle}>
      {children}
    </button>
  )
}

function Field({ label, children }) {
  return (
    <div className="block space-y-1 text-sm">
      <span className="font-medium text-white/85">{label}</span>
      {children}
    </div>
  )
}

const inputClass = glassField

export default function ClinicConsole({ onLogout, onOpenPatientApp }) {
  const { t, i18n } = useTranslation()
  const [profile, setProfile] = useState(null)
  const [tab, setTab] = useState('invoices')
  const [services, setServices] = useState([])
  const [settings, setSettings] = useState(null)
  const [patients, setPatients] = useState([])
  const [patientQuery, setPatientQuery] = useState('')
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [lineDrafts, setLineDrafts] = useState([{ service_id: '', variant_id: '', quantity: 1 }])
  const [discountPercent, setDiscountPercent] = useState('')
  const [discountReason, setDiscountReason] = useState('friends')
  const [discountCustom, setDiscountCustom] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('cash')
  const [invoices, setInvoices] = useState([])
  const [report, setReport] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [plans, setPlans] = useState([])
  const [planForm, setPlanForm] = useState({
    name: 'خطة تغذية',
    activity_level: 'moderately_active',
    calorie_target: 1600,
    calorie_target_reason: '',
    macro_entry_mode: 'percent',
    macro_template: 'balanced',
    protein_pct: 30,
    carbs_pct: 40,
    fats_pct: 30,
    treatment_objective: '',
  })
  const [energyPreview, setEnergyPreview] = useState(null)
  const [macroPreview, setMacroPreview] = useState(null)

  const isDoctor = profile?.clinic_role === 'doctor'
  const isAr = i18n.language?.startsWith('ar')
  const brandName =
    (isAr ? settings?.clinic_name_ar : settings?.clinic_name_en) || t('common.appName')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const me = await fetchMyProfile()
        if (cancelled) return
        setProfile(me)
        const [svc, sett, inv, rep] = await Promise.all([
          clinicApi.services(),
          clinicApi.settings(),
          clinicApi.invoices(),
          clinicApi.revenueReport(),
        ])
        if (cancelled) return
        setServices(svc.data || [])
        setSettings(sett.data || null)
        setInvoices(inv.data || [])
        setReport(rep.data || null)
        if (me.clinic_role === 'doctor') {
          const planRes = await nutritionPlansApi.list()
          if (!cancelled) setPlans(planRes.data || [])
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || 'تعذر تحميل لوحة العيادة')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const { data } = await clinicApi.patients(patientQuery)
        setPatients(data || [])
      } catch {
        setPatients([])
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [patientQuery])

  const selectedServiceMap = useMemo(() => {
    const map = new Map(services.map((s) => [String(s.id), s]))
    return map
  }, [services])

  async function refreshInvoicesAndReport() {
    const [inv, rep] = await Promise.all([clinicApi.invoices(), clinicApi.revenueReport()])
    setInvoices(inv.data || [])
    setReport(rep.data || null)
  }

  async function handleCreateInvoice() {
    setError('')
    setMessage('')
    if (!selectedPatient) {
      setError('اختر مريضاً أولاً')
      return
    }
    const chosen = lineDrafts.filter((l) => l.service_id)
    if (!chosen.length) {
      setError('اختر خدمة من القائمة قبل إصدار الفاتورة')
      return
    }
    for (const line of chosen) {
      const svc = selectedServiceMap.get(String(line.service_id))
      if (svc?.has_price_variants && !line.variant_id) {
        setError(`اختر الجرعة للخدمة «${svc.name_ar}»`)
        return
      }
    }
    const items = chosen.map((l) => {
      const svc = selectedServiceMap.get(String(l.service_id))
      return {
        service_id: Number(l.service_id),
        variant_id: l.variant_id ? Number(l.variant_id) : undefined,
        quantity: svc?.allow_quantity ? Number(l.quantity) || 1 : 1,
      }
    })
    try {
      const payload = {
        patient_id: selectedPatient.user_id,
        items,
        notes: '',
      }
      if (!payload.patient_id) {
        setError('معرّف المريض غير متاح — حدّث البحث')
        return
      }
      if (discountPercent) {
        payload.discount_percent = Number(discountPercent)
        payload.discount_reason = discountReason
        payload.discount_reason_custom = discountCustom
      }
      const { data: invoice } = await clinicApi.createInvoice(payload)
      try {
        await clinicApi.payInvoice(invoice.id, {
          amount_paid_iqd: invoice.total_due_iqd,
          payment_method: paymentMethod,
        })
        setMessage(`تم إصدار الفاتورة رقم ${String(invoice.invoice_number).padStart(6, '0')}`)
      } catch (payErr) {
        setError(
          `تم إنشاء الفاتورة رقم ${String(invoice.invoice_number).padStart(6, '0')} لكن تعذر تسجيل الدفع: ${clinicErrorMessage(payErr)}`,
        )
      }
      setLineDrafts([{ service_id: '', variant_id: '', quantity: 1 }])
      setDiscountPercent('')
      await refreshInvoicesAndReport()
    } catch (err) {
      setError(clinicErrorMessage(err, 'تعذر إصدار الفاتورة'))
    }
  }

  async function runEnergyPreview() {
    if (!selectedPatient?.user_id) return
    const { data } = await nutritionPlansApi.energyPreview({
      patient_id: selectedPatient.user_id,
      activity_level: planForm.activity_level,
      calorie_target: Number(planForm.calorie_target),
    })
    setEnergyPreview(data)
  }

  async function runMacroPreview() {
    const { data } = await nutritionPlansApi.macroPreview({
      calorie_target: Number(planForm.calorie_target),
      macro_entry_mode: planForm.macro_entry_mode,
      macro_template: planForm.macro_template,
      protein_pct: Number(planForm.protein_pct),
      carbs_pct: Number(planForm.carbs_pct),
      fats_pct: Number(planForm.fats_pct),
    })
    setMacroPreview(data)
  }

  async function createPlan() {
    setError('')
    setMessage('')
    if (!selectedPatient?.user_id) {
      setError('اختر مريضاً')
      return
    }
    try {
      const { data } = await nutritionPlansApi.create({
        patient_id: selectedPatient.user_id,
        ...planForm,
        calorie_target: Number(planForm.calorie_target),
        protein_pct: Number(planForm.protein_pct),
        carbs_pct: Number(planForm.carbs_pct),
        fats_pct: Number(planForm.fats_pct),
        meal_items: [
          {
            day_of_week: 1,
            meal_slot: 'breakfast',
            meal_time: '08:00:00',
            food_name: 'وجبة إفطار (يُكملها الطبيب)',
            quantity: 1,
            unit: 'serving',
            calories: Math.round(Number(planForm.calorie_target) * 0.25),
            protein_g: 0,
            carbs_g: 0,
            fats_g: 0,
            alternative_name: '',
            instructions: '',
          },
        ],
      })
      setMessage(`تم حفظ مسودة الخطة: ${data.name}`)
      const planRes = await nutritionPlansApi.list()
      setPlans(planRes.data || [])
    } catch (err) {
      setError(JSON.stringify(err.response?.data || err.message))
    }
  }

  async function approvePlan(id) {
    await nutritionPlansApi.approve(id)
    const planRes = await nutritionPlansApi.list()
    setPlans(planRes.data || [])
    setMessage('تم اعتماد وإرسال الخطة للمريض')
  }

  async function toggleTdeeVisibility() {
    if (!selectedPatient?.user_id) return
    try {
      const next = !selectedPatient.show_tdee_calculator
      const { data } = await clinicApi.setPatientTdeeVisibility(selectedPatient.user_id, next)
      setSelectedPatient(data)
      setPatients((rows) => rows.map((row) => (row.user_id === data.user_id ? data : row)))
      setMessage(
        next
          ? 'تم إظهار حاسبة معدل الطاقة لهذا المريض'
          : 'تم إخفاء حاسبة معدل الطاقة عن هذا المريض',
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'تعذر تحديث الصلاحية')
    }
  }

  return (
    <div className="min-h-screen text-white" style={glassPageBg} dir="rtl">
      <header className={glassHeader}>
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <p className="text-xs tracking-[0.2em] text-white/60">{brandName}</p>
            <h1 className="text-2xl font-bold text-white">{brandName}</h1>
            <p className="text-sm text-white/75">
              {profile?.clinic_role === 'doctor' ? 'الطبيبة / المدير' : 'السكرتيرة'} ·{' '}
              {profile?.full_name || profile?.phone}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <LanguageSwitcher variant="glass" />
            {onOpenPatientApp ? (
              <button type="button" onClick={onOpenPatientApp} className={glassBtnGhost}>
                تطبيق المريض
              </button>
            ) : null}
            <button type="button" onClick={onLogout} className={glassBtnDanger}>
              {t('common.signOut')}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-5 px-4 py-6">
        <div className="flex flex-wrap gap-2">
          <TabButton active={tab === 'invoices'} onClick={() => setTab('invoices')}>
            الفواتير
          </TabButton>
          <TabButton active={tab === 'services'} onClick={() => setTab('services')}>
            دليل الخدمات
          </TabButton>
          <TabButton active={tab === 'reports'} onClick={() => setTab('reports')}>
            تقارير الإيرادات
          </TabButton>
          {isDoctor ? (
            <TabButton active={tab === 'tdee'} onClick={() => setTab('tdee')}>
              معدل الطاقة
            </TabButton>
          ) : null}
          {isDoctor ? (
            <TabButton active={tab === 'plans'} onClick={() => setTab('plans')}>
              الخطط الغذائية
            </TabButton>
          ) : null}
        </div>

        {message ? <p className={glassAlertOk}>{message}</p> : null}
        {error ? <p className={glassAlertErr}>{error}</p> : null}

        <section className={glassPanel}>
          <h2 className="mb-3 text-base font-bold text-white">اختيار المريض</h2>
          <input
            className={inputClass}
            placeholder="بحث بالاسم / الهاتف / رقم الملف"
            value={patientQuery}
            onChange={(e) => setPatientQuery(e.target.value)}
          />
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {patients.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedPatient(p)}
                className={`rounded-2xl border px-3 py-2 text-right text-sm transition ${
                  selectedPatient?.id === p.id
                    ? 'border-white bg-white/25 text-white ring-1 ring-white/40'
                    : 'border-white/25 bg-white/10 text-white/90 hover:bg-white/15'
                }`}
              >
                <div className="font-semibold">{p.full_name || p.phone}</div>
                <div className="text-xs text-white/65">
                  {p.phone} · ملف {p.patient_file_number || '—'}
                  {p.show_tdee_calculator ? ' · TDEE مفعّل' : ''}
                </div>
              </button>
            ))}
          </div>

          {isDoctor && selectedPatient?.user_id ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/20 bg-white/10 px-3 py-3 backdrop-blur-sm">
              <div>
                <p className="text-sm font-semibold text-white">
                  {selectedPatient.full_name || selectedPatient.phone} · حاسبة معدل الطاقة
                </p>
                <p className="text-xs text-white/65">
                  الحاسبة كاملة عند الطبيبة. المريض يراها فقط بعد التفعيل.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className={glassBtnWhite} onClick={() => setTab('tdee')}>
                  فتح الحاسبة الكاملة
                </button>
                <button
                  type="button"
                  className={selectedPatient.show_tdee_calculator ? glassBtnDanger : glassBtnWhite}
                  onClick={toggleTdeeVisibility}
                >
                  {selectedPatient.show_tdee_calculator ? 'إخفاء عن المريض' : 'إظهار للمريض'}
                </button>
              </div>
            </div>
          ) : null}
        </section>

        {tab === 'tdee' && isDoctor ? (
          <section className="space-y-4">
            {!selectedPatient?.user_id ? (
              <p className={glassAlertWarn}>اختر مريضاً أولاً لحساب معدل الطاقة وحفظ الأهداف على ملفه.</p>
            ) : (
              <>
                <div className={`${glassPanel} flex flex-wrap items-center justify-between gap-3`}>
                  <div>
                    <p className="text-sm font-bold text-white">
                      حساب معدل الطاقة لـ {selectedPatient.full_name || selectedPatient.phone}
                    </p>
                    <p className="text-xs text-white/65">
                      احسب BMR + TEA + TEF، حدّد العجز والماكروز، ثم احفظها على ملف المريض.
                    </p>
                  </div>
                  <button
                    type="button"
                    className={selectedPatient.show_tdee_calculator ? glassBtnDanger : glassBtnWhite}
                    onClick={toggleTdeeVisibility}
                  >
                    {selectedPatient.show_tdee_calculator ? 'إخفاء عن المريض' : 'إظهار للمريض'}
                  </button>
                </div>
                <TdeeCalculator
                  key={selectedPatient.user_id}
                  initialProfile={selectedPatient}
                  showHowTo={false}
                  applyLabel="حفظ الأهداف على ملف المريض"
                  applyTargets={async (payload) => {
                    const { data } = await clinicApi.setPatientEnergyTargets(
                      selectedPatient.user_id,
                      payload,
                    )
                    setSelectedPatient(data)
                    setPatients((rows) =>
                      rows.map((row) => (row.user_id === data.user_id ? data : row)),
                    )
                    setMessage('تم حفظ أهداف الطاقة والماكروز على ملف المريض')
                  }}
                />
              </>
            )}
          </section>
        ) : null}

        {tab === 'invoices' ? (
          <section className="space-y-4">
            <div className={glassPanel}>
              <h2 className="mb-3 text-base font-bold text-white">إنشاء فاتورة</h2>
              <div className="space-y-3">
                {!services.length ? (
                  <p className={glassAlertWarn}>
                    دليل الخدمات غير محمّل. تأكد أن الخادم يعمل ثم حدّث الصفحة.
                  </p>
                ) : null}
                {lineDrafts.map((line, idx) => {
                  const svc = selectedServiceMap.get(String(line.service_id))
                  const variant = (svc?.variants || []).find(
                    (v) => String(v.id) === String(line.variant_id),
                  )
                  const unit = variant ? variant.price_iqd : svc?.base_price_iqd
                  const qty = svc?.allow_quantity ? Number(line.quantity) || 1 : 1
                  const lineTotal =
                    svc && (!svc.has_price_variants || variant) ? Number(unit) * qty : null
                  const serviceOptions = services
                    .filter((s) => !s.is_free_follow_up)
                    .map((s) => ({
                      value: String(s.id),
                      label: `${s.name_ar} (${formatIqd(s.base_price_iqd)})`,
                    }))
                  const variantOptions = (svc?.variants || []).map((v) => ({
                    value: String(v.id),
                    label: `${v.label_ar} (${formatIqd(v.price_iqd)})`,
                  }))
                  return (
                    <div
                      key={idx}
                      className="grid gap-2 rounded-2xl border border-white/15 bg-white/5 p-3 sm:grid-cols-4"
                    >
                      <Field label="الخدمة">
                        <GlassSelect
                          shape="field"
                          placeholder="اختر الخدمة"
                          value={line.service_id}
                          options={serviceOptions}
                          onChange={(value) => {
                            const picked = selectedServiceMap.get(String(value))
                            const next = [...lineDrafts]
                            next[idx] = {
                              ...next[idx],
                              service_id: value,
                              variant_id: '',
                              quantity: picked?.allow_quantity ? next[idx].quantity || 1 : 1,
                            }
                            setLineDrafts(next)
                            setError('')
                          }}
                        />
                      </Field>
                      <Field label="الجرعة / المتغير">
                        <GlassSelect
                          shape="field"
                          placeholder={svc?.has_price_variants ? 'اختر الجرعة' : '—'}
                          value={line.variant_id}
                          disabled={!svc?.has_price_variants}
                          options={variantOptions}
                          onChange={(value) => {
                            const next = [...lineDrafts]
                            next[idx] = { ...next[idx], variant_id: value }
                            setLineDrafts(next)
                            setError('')
                          }}
                        />
                      </Field>
                      <Field label="الكمية">
                        <input
                          type="number"
                          min="1"
                          className={inputClass}
                          value={svc && !svc.allow_quantity ? 1 : line.quantity}
                          disabled={!svc?.allow_quantity}
                          onChange={(e) => {
                            const next = [...lineDrafts]
                            next[idx] = { ...next[idx], quantity: e.target.value }
                            setLineDrafts(next)
                          }}
                        />
                      </Field>
                      <div className="flex items-end">
                        <button
                          type="button"
                          className={`w-full ${glassBtnGhost}`}
                          onClick={() =>
                            setLineDrafts((rows) =>
                              rows.length === 1
                                ? [{ service_id: '', variant_id: '', quantity: 1 }]
                                : rows.filter((_, i) => i !== idx),
                            )
                          }
                        >
                          حذف
                        </button>
                      </div>
                      {lineTotal != null ? (
                        <p className="text-sm text-white/80 sm:col-span-4">
                          المجموع: {formatIqd(lineTotal)}
                        </p>
                      ) : null}
                    </div>
                  )
                })}
                <button
                  type="button"
                  className={glassBtnGhost}
                  onClick={() =>
                    setLineDrafts((rows) => [...rows, { service_id: '', variant_id: '', quantity: 1 }])
                  }
                >
                  + خدمة
                </button>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <Field label={`خصم % (افتراضي ${settings?.default_discount_percent ?? 20})`}>
                  <input
                    className={inputClass}
                    value={discountPercent}
                    onChange={(e) => setDiscountPercent(e.target.value)}
                    placeholder="مثلاً 20"
                  />
                </Field>
                <Field label="سبب الخصم">
                  <GlassSelect
                    shape="field"
                    value={discountReason}
                    options={DISCOUNT_REASONS}
                    onChange={setDiscountReason}
                  />
                </Field>
                <Field label="سبب مخصص">
                  <input
                    className={inputClass}
                    value={discountCustom}
                    onChange={(e) => setDiscountCustom(e.target.value)}
                  />
                </Field>
                <Field label="طريقة الدفع">
                  <GlassSelect
                    shape="field"
                    value={paymentMethod}
                    options={[
                      { value: 'cash', label: 'نقداً' },
                      {
                        value: 'master_qi_card',
                        label: `Master Qi Card (${settings?.master_qi_card_number || ''})`,
                      },
                    ]}
                    onChange={setPaymentMethod}
                  />
                </Field>
              </div>

              {error ? <p className={`mt-4 ${glassAlertErr}`}>{error}</p> : null}

              <button type="button" onClick={handleCreateInvoice} className={`mt-4 ${glassBtnWhite}`}>
                إصدار فاتورة وتسجيل الدفع
              </button>
            </div>

            <div className={glassPanel}>
              <h2 className="mb-3 text-base font-bold text-white">آخر الفواتير</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-white/90">
                  <thead>
                    <tr className="border-b border-white/20 text-white/60">
                      <th className="px-2 py-2 text-right font-medium">الرقم</th>
                      <th className="px-2 py-2 text-right font-medium">المريض</th>
                      <th className="px-2 py-2 text-right font-medium">المستحق</th>
                      <th className="px-2 py-2 text-right font-medium">الحالة</th>
                      <th className="px-2 py-2 text-right font-medium">الدفع</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={inv.id} className="border-b border-white/10">
                        <td className="px-2 py-2 font-mono">
                          {String(inv.invoice_number).padStart(6, '0')}
                        </td>
                        <td className="px-2 py-2">{inv.patient_name_snapshot || inv.patient_phone}</td>
                        <td className="px-2 py-2">{formatIqd(inv.total_due_iqd)}</td>
                        <td className="px-2 py-2">{inv.payment_status}</td>
                        <td className="px-2 py-2">{inv.payment_method || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        ) : null}

        {tab === 'services' ? (
          <section className={glassPanel}>
            <h2 className="mb-3 text-base font-bold text-white">دليل الخدمات والأسعار (د.ع)</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {services.map((s) => (
                <article
                  key={s.id}
                  className="rounded-2xl border border-white/20 bg-white/10 p-3 backdrop-blur-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-white">{s.name_ar}</h3>
                      <p className="text-xs text-white/60">{s.unit_label_ar}</p>
                    </div>
                    <p className="font-bold text-white">{formatIqd(s.base_price_iqd)}</p>
                  </div>
                  {s.variants?.length ? (
                    <ul className="mt-2 space-y-1 text-xs text-white/75">
                      {s.variants.map((v) => (
                        <li key={v.id} className="flex justify-between">
                          <span>{v.label_ar}</span>
                          <span>{formatIqd(v.price_iqd)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {tab === 'reports' ? (
          <section className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className={`${glassStat} !bg-white/20 text-start`}>
                <p className="text-xs text-white/70">إجمالي المقبوض</p>
                <p className="mt-1 text-xl font-bold text-white">
                  {formatIqd(report?.totals?.revenue_iqd)}
                </p>
              </div>
              <div className={`${glassStat} text-start`}>
                <p className="text-xs text-white/70">المستحق</p>
                <p className="mt-1 text-xl font-bold text-white">{formatIqd(report?.totals?.due_iqd)}</p>
              </div>
              <div className={`${glassStat} text-start`}>
                <p className="text-xs text-white/70">الخصومات</p>
                <p className="mt-1 text-xl font-bold text-white">
                  {formatIqd(report?.totals?.discounts_iqd)}
                </p>
              </div>
              <div className={`${glassStat} text-start`}>
                <p className="text-xs text-white/70">عدد الفواتير</p>
                <p className="mt-1 text-xl font-bold text-white">{report?.totals?.invoice_count ?? 0}</p>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div className={glassPanel}>
                <h3 className="mb-2 font-bold text-white">حسب طريقة الدفع</h3>
                <ul className="space-y-1 text-sm text-white/85">
                  {(report?.by_payment_method || []).map((row) => (
                    <li key={row.payment_method || 'none'} className="flex justify-between">
                      <span>{row.payment_method || '—'}</span>
                      <span>{formatIqd(row.total)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className={glassPanel}>
                <h3 className="mb-2 font-bold text-white">مونجارو حسب الجرعة</h3>
                <ul className="space-y-1 text-sm text-white/85">
                  {(report?.mounjaro_by_dose || []).map((row) => (
                    <li key={row.variant_label_snapshot || 'x'} className="flex justify-between">
                      <span>{row.variant_label_snapshot || '—'}</span>
                      <span>
                        {row.count} · {formatIqd(row.revenue)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ) : null}

        {tab === 'plans' && isDoctor ? (
          <section className="space-y-4">
            <div className={glassPanel}>
              <h2 className="mb-3 text-base font-bold text-white">محرر الخطة الغذائية (الطبيب)</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="اسم الخطة">
                  <input
                    className={inputClass}
                    value={planForm.name}
                    onChange={(e) => setPlanForm((f) => ({ ...f, name: e.target.value }))}
                  />
                </Field>
                <Field label="مستوى النشاط">
                  <select
                    className={inputClass}
                    value={planForm.activity_level}
                    onChange={(e) => setPlanForm((f) => ({ ...f, activity_level: e.target.value }))}
                  >
                    {ACTIVITY_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="السعرات المعتمدة">
                  <input
                    type="number"
                    className={inputClass}
                    value={planForm.calorie_target}
                    onChange={(e) => setPlanForm((f) => ({ ...f, calorie_target: e.target.value }))}
                  />
                </Field>
                <Field label="قالب الماكروز">
                  <select
                    className={inputClass}
                    value={planForm.macro_template}
                    onChange={(e) => setPlanForm((f) => ({ ...f, macro_template: e.target.value }))}
                  >
                    <option value="balanced">متوازن 25/45/30</option>
                    <option value="higher_protein">بروتين أعلى 30/40/30</option>
                    <option value="moderate_carb">كارب معتدل 30/35/35</option>
                    <option value="custom">مخصص</option>
                  </select>
                </Field>
                <Field label="بروتين %">
                  <input
                    type="number"
                    className={inputClass}
                    value={planForm.protein_pct}
                    onChange={(e) =>
                      setPlanForm((f) => ({ ...f, protein_pct: e.target.value, macro_template: 'custom' }))
                    }
                  />
                </Field>
                <Field label="كارب %">
                  <input
                    type="number"
                    className={inputClass}
                    value={planForm.carbs_pct}
                    onChange={(e) =>
                      setPlanForm((f) => ({ ...f, carbs_pct: e.target.value, macro_template: 'custom' }))
                    }
                  />
                </Field>
                <Field label="دهون %">
                  <input
                    type="number"
                    className={inputClass}
                    value={planForm.fats_pct}
                    onChange={(e) =>
                      setPlanForm((f) => ({ ...f, fats_pct: e.target.value, macro_template: 'custom' }))
                    }
                  />
                </Field>
                <Field label="سبب هدف السعرات">
                  <input
                    className={inputClass}
                    value={planForm.calorie_target_reason}
                    onChange={(e) =>
                      setPlanForm((f) => ({ ...f, calorie_target_reason: e.target.value }))
                    }
                  />
                </Field>
                <Field label="هدف العلاج">
                  <input
                    className={inputClass}
                    value={planForm.treatment_objective}
                    onChange={(e) =>
                      setPlanForm((f) => ({ ...f, treatment_objective: e.target.value }))
                    }
                  />
                </Field>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className={glassBtnGhost} onClick={runEnergyPreview}>
                  معاينة BMR/TDEE
                </button>
                <button type="button" className={glassBtnGhost} onClick={runMacroPreview}>
                  تحويل الماكروز
                </button>
                <button type="button" className={glassBtnWhite} onClick={createPlan}>
                  حفظ مسودة
                </button>
              </div>
              {energyPreview ? (
                <div className="mt-3 rounded-2xl border border-emerald-200/30 bg-emerald-400/15 p-3 text-sm text-white">
                  BMR {energyPreview.bmr_kcal} · TDEE {energyPreview.tdee_kcal} · الهدف{' '}
                  {energyPreview.calorie_target} ({energyPreview.calorie_vs_tdee_diff} /{' '}
                  {energyPreview.calorie_vs_tdee_pct}%)
                  {energyPreview.is_paediatric_pathway ? ' · مسار أطفال' : ''}
                </div>
              ) : null}
              {macroPreview ? (
                <div className="mt-2 rounded-2xl border border-sky-200/30 bg-sky-400/15 p-3 text-sm text-white">
                  بروتين {macroPreview.protein_g}غ · كارب {macroPreview.carbs_g}غ · دهون{' '}
                  {macroPreview.fats_g}غ
                </div>
              ) : null}
            </div>

            <div className={glassPanel}>
              <h3 className="mb-2 font-bold text-white">الخطط</h3>
              <ul className="space-y-2 text-sm">
                {plans.map((p) => (
                  <li
                    key={p.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/20 bg-white/5 px-3 py-2"
                  >
                    <div>
                      <div className="font-semibold text-white">{p.name}</div>
                      <div className="text-xs text-white/60">
                        {p.patient_name} · v{p.current_version} · {p.status}
                        {p.is_paediatric_pathway ? ' · paediatric' : ''}
                      </div>
                    </div>
                    {p.status === 'draft' ? (
                      <button
                        type="button"
                        className={glassBtnWhite}
                        onClick={() => approvePlan(p.id)}
                      >
                        اعتماد وإرسال
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          </section>
        ) : null}
      </main>
    </div>
  )
}
