import api from './axios'

export async function fetchWeightLogs() {
  const { data } = await api.get('/profile/weight-logs/')
  return data
}

export async function addWeightLog({ weight_kg, recorded_at, note = '' }) {
  const { data } = await api.post('/profile/weight-logs/', {
    weight_kg,
    recorded_at,
    note,
  })
  return data
}
