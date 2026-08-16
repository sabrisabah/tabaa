import axios from 'axios'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: ({ access, refresh }) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const url = originalRequest?.url ?? ''
    const isAuthRequest =
      url.includes('/auth/token/') ||
      url.includes('/auth/token/refresh/') ||
      url.includes('/auth/register/') ||
      url.includes('/profile/tdee-preview/')

    const emitLogout = () => {
      tokenStorage.clear()
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:logout'))
      }
    }

    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      isAuthRequest
    ) {
      return Promise.reject(error)
    }

    const refresh = tokenStorage.getRefresh()
    if (!refresh) {
      emitLogout()
      return Promise.reject(error)
    }

    originalRequest._retry = true

    if (!refreshPromise) {
      refreshPromise = axios
        .post('/api/auth/token/refresh/', { refresh })
        .then(({ data }) => {
          tokenStorage.setTokens({
            access: data.access,
            refresh: data.refresh ?? refresh,
          })
          return data.access
        })
        .catch((refreshError) => {
          emitLogout()
          throw refreshError
        })
        .finally(() => {
          refreshPromise = null
        })
    }

    try {
      const newAccess = await refreshPromise
      originalRequest.headers.Authorization = `Bearer ${newAccess}`
      return api(originalRequest)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  },
)

export default api
