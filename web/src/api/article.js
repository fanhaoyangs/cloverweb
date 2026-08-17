/**
 * 公共文章 API（仅读，Django 后端）
 * 后端字段 snake_case，此处映射为前端 camelCase
 */
import request from '@/utils/request'

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

function mapArticle(raw) {
  return {
    slug: raw.slug,
    title: raw.title,
    excerpt: raw.excerpt || '',
    coverImage: raw.cover_image || '',
    category: raw.category || '',
    categoryLabel: getCategoryLabel(raw.category),
    publishedAt: raw.published_at,
    isFeatured: raw.is_featured,
    websiteSections: raw.website_sections || [],
    viewCount: raw.view_count,
    content: raw.content_html || '',
    author: raw.author_name || ''
  }
}

export async function listArticles({ category, page = 1, pageSize = 20, websiteSection, featured } = {}) {
  const params = { page, page_size: pageSize }
  if (category) params.category = category
  if (websiteSection) params.section = websiteSection
  if (featured) params.featured = 1
  try {
    const { data } = await request.get('/articles/', { params })
    return {
      code: 0,
      data: { list: (data.results || []).map(mapArticle), total: data.count || 0 }
    }
  } catch (e) {
    return { code: -1, message: e.message, data: { list: [], total: 0 } }
  }
}

export async function getArticleBySlug(slug) {
  try {
    const { data } = await request.get(`/articles/${slug}/`)
    return { code: 0, data: mapArticle(data) }
  } catch (e) {
    if (e.response && e.response.status === 404) {
      return { code: 404, message: '文章不存在' }
    }
    return { code: -1, message: e.message }
  }
}

/**
 * 兼容旧调用：浏览量由后端在详情接口自动累计，无需前端调用
 */
export async function incrementView() {}
