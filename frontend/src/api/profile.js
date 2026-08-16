import api from './axios'

export async function fetchMyProfile() {
  const { data } = await api.get('/profile/me/')
  return data
}

export async function createMyProfile(payload) {
  const { data } = await api.post('/profile/me/', payload)
  return data
}

export async function updateMyProfile(payload) {
  const { data } = await api.patch('/profile/me/', payload)
  return data
}

export async function previewTdee(payload) {
  const { data } = await api.post('/profile/tdee-preview/', payload)
  return data
}
