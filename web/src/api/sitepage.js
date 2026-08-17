/**
 * 静态页 API（home / about / philosophy，来自 Django SitePage）
 */
import request from '@/utils/request'

export async function getSitePage(slug) {
  try {
    const { data } = await request.get(`/sitepage/${slug}/`)
    return { code: 0, data }
  } catch (e) {
    return { code: -1, message: e.message }
  }
}
