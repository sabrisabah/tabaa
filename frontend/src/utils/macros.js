/**
 * Derive consumed macros for a single meal log from API food data.
 * Used only to incrementally update displayed totals after add/remove —
 * authoritative totals still come from GET /diary/today/summary/ on mount.
 */
export function macrosFromMealLog(log) {
  const quantity = Number(log.quantity) || 0
  const food = log.food_item ?? {}

  return {
    calories: quantity * Number(food.calories ?? 0),
    protein: quantity * Number(food.protein ?? 0),
    carbs: quantity * Number(food.carbs ?? 0),
    fats: quantity * Number(food.fats ?? 0),
  }
}

export function addMacroTotals(a, b) {
  return {
    calories: a.calories + b.calories,
    protein: a.protein + b.protein,
    carbs: a.carbs + b.carbs,
    fats: a.fats + b.fats,
  }
}

export function subtractMacroTotals(a, b) {
  return {
    calories: a.calories - b.calories,
    protein: a.protein - b.protein,
    carbs: a.carbs - b.carbs,
    fats: a.fats - b.fats,
  }
}

export function computeRemaining(targets, consumed) {
  return {
    calories: targets.calories - consumed.calories,
    protein: targets.protein - consumed.protein,
    carbs: targets.carbs - consumed.carbs,
    fats: targets.fats - consumed.fats,
  }
}

export function macroPercent(consumed, target) {
  if (!target || target <= 0) return 0
  return Math.min(100, Math.round((consumed / target) * 100))
}

export function todayISO() {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function paginatedResults(data) {
  return Array.isArray(data) ? data : (data?.results ?? [])
}
