import api, { tokenStorage } from './axios'
import { toIraqLocal11 } from '../utils/phone'

export async function login(phone, password) {
  const { data } = await api.post('/auth/token/', {
    phone: toIraqLocal11(phone),
    password,
  })
  tokenStorage.setTokens({ access: data.access, refresh: data.refresh })
  return data
}

export async function register({
  phone,
  password,
  password_confirm,
  gender,
  age,
  height_cm,
  weight_kg,
  activity_level,
}) {
  const { data } = await api.post('/auth/register/', {
    phone: toIraqLocal11(phone),
    password,
    password_confirm,
    gender,
    age,
    height_cm,
    weight_kg,
    activity_level,
  })
  tokenStorage.setTokens({ access: data.access, refresh: data.refresh })
  return data
}

export function logout() {
  tokenStorage.clear()
}

export function isAuthenticated() {
  return Boolean(tokenStorage.getAccess() || tokenStorage.getRefresh())
}
