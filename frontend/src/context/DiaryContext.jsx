import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  createMealLog,
  deleteMealLog,
  fetchTodaySummary,
  getOrCreateTodayDiary,
} from '../api/diary'
import {
  addMacroTotals,
  computeRemaining,
  macrosFromMealLog,
  subtractMacroTotals,
} from '../utils/macros'

const DiaryContext = createContext(null)

const MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'snack']

const EMPTY_MACROS = { calories: 0, protein: 0, carbs: 0, fats: 0 }

export { EMPTY_MACROS }

export function DiaryProvider({ children }) {
  const [todayDiary, setTodayDiary] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [addFoodMealType, setAddFoodMealType] = useState(null)

  const mealLogs = todayDiary?.meal_logs ?? []

  const mealsByType = useMemo(() => {
    return MEAL_TYPES.reduce((acc, type) => {
      acc[type] = mealLogs.filter((log) => log.meal_type === type)
      return acc
    }, {})
  }, [mealLogs])

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [diary, summaryData] = await Promise.all([
        getOrCreateTodayDiary(),
        fetchTodaySummary(),
      ])
      setTodayDiary(diary)
      setSummary(summaryData)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        detail ??
          'Unable to load your diary. Make sure you are logged in and have a profile.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  const needsProfile =
    typeof error === 'string' &&
    /complete your profile/i.test(error)

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const openAddFood = useCallback((mealType) => {
    setAddFoodMealType(mealType)
  }, [])

  const closeAddFood = useCallback(() => {
    setAddFoodMealType(null)
  }, [])

  const addMealLog = useCallback(
    async ({ foodItemId, quantity, mealType }) => {
      if (!todayDiary?.id) return

      const created = await createMealLog({
        daily_diary: todayDiary.id,
        meal_type: mealType ?? addFoodMealType,
        food_item_id: foodItemId,
        quantity,
      })

      setTodayDiary((prev) => ({
        ...prev,
        meal_logs: [...(prev?.meal_logs ?? []), created],
      }))

      const delta = macrosFromMealLog(created)
      setSummary((prev) => {
        if (!prev) return prev
        const consumed = addMacroTotals(prev.consumed, delta)
        return {
          ...prev,
          consumed,
          remaining: computeRemaining(prev.targets, consumed),
        }
      })

      closeAddFood()
      return created
    },
    [todayDiary?.id, addFoodMealType, closeAddFood],
  )

  const removeMealLog = useCallback(async (logId) => {
    const log = mealLogs.find((entry) => entry.id === logId)
    if (!log) return

    await deleteMealLog(logId)

    setTodayDiary((prev) => ({
      ...prev,
      meal_logs: (prev?.meal_logs ?? []).filter((entry) => entry.id !== logId),
    }))

    const delta = macrosFromMealLog(log)
    setSummary((prev) => {
      if (!prev) return prev
      const consumed = subtractMacroTotals(prev.consumed, delta)
      return {
        ...prev,
        consumed,
        remaining: computeRemaining(prev.targets, consumed),
      }
    })
  }, [mealLogs])

  const value = useMemo(
    () => ({
      todayDiary,
      summary,
      mealLogs,
      mealsByType,
      loading,
      error,
      needsProfile,
      addFoodMealType,
      openAddFood,
      closeAddFood,
      addMealLog,
      removeMealLog,
      refreshDashboard: loadDashboard,
      mealTypes: MEAL_TYPES,
    }),
    [
      todayDiary,
      summary,
      mealLogs,
      mealsByType,
      loading,
      error,
      needsProfile,
      addFoodMealType,
      openAddFood,
      closeAddFood,
      addMealLog,
      removeMealLog,
      loadDashboard,
    ],
  )

  return <DiaryContext.Provider value={value}>{children}</DiaryContext.Provider>
}

export function useDiary() {
  const context = useContext(DiaryContext)
  if (!context) {
    throw new Error('useDiary must be used within a DiaryProvider')
  }
  return context
}
