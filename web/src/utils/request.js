/**
 * axios 实例：统一走 Django 后端 /api
 */
import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API error:', error.config?.url, error.message)
    return Promise.reject(error)
  }
)

export default request
