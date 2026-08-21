/**
 * 静态页 API（来自 Django SitePage）
 */
import request from '@/utils/request'

export async function getSitePage(slug) {
  try {
    const { data } = await request.get(`/sitepage/${slug}/`)
    return { code: 0, data }
  } catch (e) {
    return { code: e?.response?.status || -1, message: e.message }
  }
}

/** 公开导航列表：仅已发布且 in_menu 的页面（SiteHeader 动态菜单用） */
export async function listSitePagesPublic() {
  const { data } = await request.get('/sitepages/')
  return Array.isArray(data) ? data : (data.results || [])
}
