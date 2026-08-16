import api from './axios'

export async function fetchSubscriptionStatus() {
  const { data } = await api.get('/subscriptions/me/')
  return data
}

export async function fetchSubscriptionPlans() {
  const { data } = await api.get('/subscriptions/plans/')
  return data
}

export async function createSubscription(planCode = 'monthly') {
  const { data } = await api.post('/subscriptions/subscribe/', {
    plan_code: planCode,
  })
  return data
}

export async function confirmTransfer(payload) {
  const { data } = await api.post('/subscriptions/confirm-transfer/', payload)
  return data
}
