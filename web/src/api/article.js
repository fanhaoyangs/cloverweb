/**
 * 公共文章 API（仅读）
 * 当前用 CloudBase 数据源，Phase 2 迁到 Django 后端
 */
import cloudBase from '@/cloud'

export const CATEGORIES = [
  { value: 'news', label: '新闻资讯' },
  { value: 'project', label: '项目案例' },
  { value: 'competition', label: '竞赛信息' },
  { value: 'media', label: '媒体报道' },
  { value: 'activity', label: '活动动态' },
  { value: 'publication', label: '学术出版' },
  { value: 'other', label: '其他' }
]

export function getCategoryLabel(value) {
  const cat = CATEGORIES.find(c => c.value === value)
  return cat ? cat.label : value
}

export async function listArticles({ category, page = 1, pageSize = 20, websiteSection } = {}) {
  await cloudBase.init()
  const db = cloudBase.getDatabase()
  const _ = db.command

  const where = { status: 'published' }
  if (category) where.category = category
  if (websiteSection) where.websiteSections = _.elemMatch(_.eq(websiteSection))

  const res = await db.collection('articles')
    .where(where)
    .orderBy('publishedAt', 'desc')
    .skip((page - 1) * pageSize)
    .limit(pageSize)
    .get()

  return { code: 0, data: res.data || [] }
}

export async function getArticleById(articleId) {
  await cloudBase.init()
  const db = cloudBase.getDatabase()
  try {
    const res = await db.collection('articles').doc(articleId).get()
    if (res.data && res.data.length > 0) {
      return { code: 0, data: res.data[0] }
    }
    return { code: 404, message: '文章不存在' }
  } catch (e) {
    return { code: -1, message: e.message }
  }
}

export async function incrementView(articleId) {
  await cloudBase.init()
  const db = cloudBase.getDatabase()
  const _ = db.command
  try {
    await db.collection('articles').doc(articleId).update({
      viewCount: _.inc(1)
    })
  } catch (e) {
    console.warn('incrementView failed', e)
  }
}
