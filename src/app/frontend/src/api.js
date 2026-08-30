// 统一 API 请求封装：自动携带 token，401 时跳转登录页
export const TOKEN_KEY = 'idss_token'
export const USER_KEY = 'idss_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export function storeSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (options.body && !(options.body instanceof FormData) && typeof options.body !== 'string') {
    headers['Content-Type'] = 'application/json'
    options = { ...options, body: JSON.stringify(options.body) }
  }

  let resp
  try {
    resp = await fetch(`/api${path}`, { ...options, headers })
  } catch (e) {
    throw new ApiError(0, '网络错误：无法连接服务器')
  }

  if (resp.status === 401 && !path.startsWith('/auth/login')) {
    clearSession()
    if (!location.hash.includes('/login')) {
      location.hash = '#/login'
    }
    throw new ApiError(401, '未登录或登录已过期')
  }

  if (!resp.ok) {
    let msg = `请求失败 (${resp.status})`
    try {
      const data = await resp.json()
      if (data.detail) {
        msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
      }
    } catch { /* 保留默认消息 */ }
    throw new ApiError(resp.status, msg)
  }

  const ct = resp.headers.get('content-type') || ''
  if (ct.includes('application/json')) return resp.json()
  return resp
}

export const api = {
  get: (path, params) => {
    const qs = params ? '?' + new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    ) : ''
    return request(path + qs)
  },
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  delete: (path) => request(path, { method: 'DELETE' }),
  upload: (path, formData) => request(path, { method: 'POST', body: formData }),
}

export function download(path, filename) {
  const a = document.createElement('a')
  a.href = `/api${path}${path.includes('?') ? '&' : '?'}token=${getToken()}`
  a.download = filename || ''
  a.click()
}
