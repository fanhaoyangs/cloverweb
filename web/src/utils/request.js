/**
 * axios 实例：统一走 Django 后端 /api
 * - 自动带 CMS JWT（Bearer）
 * - 401 时清除登录态并跳 CMS 登录页（仅管理端接口）
 */
import axios from 'axios'
import { getToken, clearLogin } from './auth'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    // 仅管理端接口 401 时强制重登（公开接口 401 无需处理）
    if (status === 401 && url.startsWith('/admin/')) {
      clearLogin()
      if (location.pathname.startsWith('/admin') && location.pathname !== '/admin/login') {
        location.href = '/admin/login'
      }
    }
    console.error('API error:', url, error.message)
    return Promise.reject(error)
  }
)

export default request
