import api from './axios'

export async function fetchWeeklyMealPlan() {
  const { data } = await api.get('/meal-plans/weekly/')
  return data
}
