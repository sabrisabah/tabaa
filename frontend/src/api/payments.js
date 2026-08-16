import api from './axios'

export async function fetchSavedCards() {
  const { data } = await api.get('/payments/card/methods/')
  return data
}

export async function deleteSavedCard(id) {
  await api.delete('/payments/card/methods/', { data: { id } })
}

export async function createCardPayment(payload) {
  const { data } = await api.post('/payments/card/create/', payload)
  return data
}

export async function fetchCardPaymentStatus(orderId) {
  const { data } = await api.get(`/payments/card/status/${orderId}/`)
  return data
}
