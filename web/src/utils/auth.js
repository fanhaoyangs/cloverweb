/**
 * CMS 登录态（轻量 store，JWT 存 localStorage）
 */
const TOKEN_KEY = 'cms_token'
const USER_KEY = 'cms_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export function setLogin({ access, user }) {
  localStorage.setItem(TOKEN_KEY, access)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearLogin() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function isLoggedIn() {
  return !!getToken()
}
