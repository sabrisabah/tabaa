import api from './axios'

export async function fetchTodaySummary() {
  const { data } = await api.get('/diary/today/summary/')
  return data
}

export async function getOrCreateTodayDiary() {
  const { data } = await api.get('/diary/today/')
  return data
}

export async function createMealLog(payload) {
  const { data } = await api.post('/meal-logs/', payload)
  return data
}

export async function deleteMealLog(id) {
  await api.delete(`/meal-logs/${id}/`)
}
