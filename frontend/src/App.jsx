import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import WeeklyMeals from './pages/WeeklyMeals'
import ClinicConsole from './pages/ClinicConsole'
import { DiaryProvider } from './context/DiaryContext'
import { isAuthenticated, logout } from './api/auth'
import { fetchMyProfile } from './api/profile'

function BrandSplash() {
  return (
    <div
      className="grid min-h-screen place-items-center"
      dir="rtl"
      style={{
        background: 'linear-gradient(145deg, #0f3d3a 0%, #134e4a 40%, #ecfdf5 100%)',
      }}
    >
      <div className="text-center text-teal-50">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-200/30 border-t-teal-100" />
        </div>
        <p className="font-[family-name:var(--font-display)] text-3xl font-bold tracking-tight">الدكتورة طيبة</p>
        <p className="mt-1 text-sm text-teal-100/70">عيادة التغذية السريرية</p>
      </div>
    </div>
  )
}

export default function App() {
  const { t, i18n } = useTranslation()
  const [authed, setAuthed] = useState(() => isAuthenticated())
  const [authView, setAuthView] = useState('login')
  const [appView, setAppView] = useState('home')
  const [openSubsFromMeals, setOpenSubsFromMeals] = useState(false)
  const [clinicRole, setClinicRole] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)

  useEffect(() => {
    document.title = t('common.appName')
  }, [t, i18n.language])

  function handleLogout() {
    logout()
    setAuthed(false)
    setAuthView('login')
    setAppView('home')
    setClinicRole(null)
  }

  useEffect(() => {
    const onAuthLogout = () => handleLogout()
    window.addEventListener('auth:logout', onAuthLogout)
    return () => window.removeEventListener('auth:logout', onAuthLogout)
  }, [])

  useEffect(() => {
    if (!authed) {
      setClinicRole(null)
      setProfileLoading(false)
      return
    }
    let cancelled = false
    setProfileLoading(true)
    fetchMyProfile()
      .then((profile) => {
        if (cancelled) return
        const role = profile?.clinic_role || 'patient'
        setClinicRole(role)
        if (role === 'doctor' || role === 'secretary') {
          setAppView('clinic')
        }
      })
      .catch((err) => {
        if (cancelled) return
        const status = err.response?.status
        if (status === 401 || status === 403 || !isAuthenticated()) {
          handleLogout()
          return
        }
        setClinicRole('patient')
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [authed])

  if (!authed) {
    if (authView === 'register') {
      return (
        <Register
          onSuccess={() => {
            setAuthed(true)
            setAppView('home')
          }}
          onGoLogin={() => setAuthView('login')}
        />
      )
    }

    return (
      <Login
        onSuccess={() => {
          setAuthed(true)
          setAppView('home')
        }}
        onGoRegister={() => setAuthView('register')}
      />
    )
  }

  if (profileLoading && clinicRole === null) {
    return <BrandSplash />
  }

  if (appView === 'clinic' && (clinicRole === 'doctor' || clinicRole === 'secretary')) {
    return (
      <ClinicConsole
        onLogout={handleLogout}
        onOpenPatientApp={() => setAppView('home')}
      />
    )
  }

  if (appView === 'meals') {
    return (
      <WeeklyMeals
        onBack={() => setAppView('home')}
        onOpenSubscriptions={() => {
          setOpenSubsFromMeals(true)
          setAppView('home')
        }}
      />
    )
  }

  return (
    <DiaryProvider>
      <Dashboard
        onLogout={handleLogout}
        onOpenMeals={() => setAppView('meals')}
        forceOpenSubscriptions={openSubsFromMeals}
        onSubscriptionsOpened={() => setOpenSubsFromMeals(false)}
        clinicRole={clinicRole}
        onOpenClinic={() => setAppView('clinic')}
      />
    </DiaryProvider>
  )
}
