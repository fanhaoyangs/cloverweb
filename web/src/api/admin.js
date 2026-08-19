/**
 * CMS 管理 API（需登录）
 */
import request from '@/utils/request'

// ---- 认证 ----
export function loginByPassword(username, password) {
  return request.post('/auth/token/', { username, password })
}

export function getFeishuLoginUrl() {
  return request.get('/auth/feishu/login/')
}

export function exchangeFeishuCode(code) {
  return request.post('/auth/feishu/exchange/', { code })
}

export function fetchMe() {
  return request.get('/auth/me/')
}

// ---- 文章 ----
export function listAdminArticles({ status, search, category, page = 1, pageSize = 20 } = {}) {
  const params = { page, page_size: pageSize }
  if (status) params.status = status
  if (search) params.search = search
  if (category) params.category = category
  return request.get('/admin/articles/', { params })
}

export function getAdminArticle(id) {
  return request.get(`/admin/articles/${id}/`)
}

export function createAdminArticle(payload) {
  return request.post('/admin/articles/', payload)
}

export function updateAdminArticle(id, payload) {
  return request.patch(`/admin/articles/${id}/`, payload)
}

export function deleteAdminArticle(id) {
  return request.delete(`/admin/articles/${id}/`)
}

// ---- 分类 ----
export function listCategories() {
  return request.get('/admin/categories/')
}

export function createCategory(name) {
  return request.post('/admin/categories/', { name })
}

// ---- 静态页 ----
export function listSitePages() {
  return request.get('/admin/sitepages/')
}

export function getSitePageAdmin(slug) {
  return request.get(`/admin/sitepages/${slug}/`)
}

export function updateSitePage(slug, payload) {
  return request.put(`/admin/sitepages/${slug}/`, payload)
}

// ---- 飞书文档导入 ----
export function getFeishuStatus() {
  return request.get('/admin/feishu/status/')
}

// 获取带文档读取权限的授权链接（导入专用，与登录授权区分）
export function getFeishuAuthorizeUrl() {
  return request.get('/admin/feishu/authorize/')
}

export function listFeishuDocuments(params) {
  return request.get('/admin/feishu/documents/', { params })
}

export function importFeishuDocument(url) {
  return request.post('/admin/feishu/import/', { url })
}

export function listFeishuHistory() {
  return request.get('/admin/feishu/history/')
}

export function listFeishuLogs() {
  return request.get('/admin/feishu/logs/')
}
