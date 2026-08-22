/**
 * BBS 论坛 API（Django /api/bbs/）
 * 后端字段 snake_case，此处映射为前端 camelCase
 */
import request from '@/utils/request'
import { isLoggedIn } from '@/utils/auth'

function mapUser(raw) {
  if (!raw) return null
  return { id: raw.id, name: raw.name, avatar: raw.avatar_url || '' }
}

function mapTopic(raw) {
  return {
    id: raw.id,
    title: raw.title,
    excerpt: raw.excerpt || '',
    node: raw.node ? { slug: raw.node.slug, name: raw.node.name, icon: raw.node.icon || '' } : null,
    author: mapUser(raw.author),
    isPinned: raw.is_pinned,
    isClosed: raw.is_closed,
    viewCount: raw.view_count,
    replyCount: raw.reply_count,
    likeCount: raw.like_count,
    liked: raw.liked,
    lastReplyAt: raw.last_reply_at,
    lastReplyUser: mapUser(raw.last_reply_user),
    createdAt: raw.created_at,
    contentHtml: raw.content_html || ''
  }
}

function mapNode(raw) {
  return {
    slug: raw.slug,
    name: raw.name,
    description: raw.description || '',
    icon: raw.icon || '',
    staffOnly: raw.staff_only,
    topicCount: raw.topic_count
  }
}

function mapPost(raw) {
  return {
    id: raw.id,
    floor: raw.floor,
    contentHtml: raw.content_html || '',
    author: mapUser(raw.author),
    likeCount: raw.like_count,
    liked: raw.liked,
    createdAt: raw.created_at
  }
}

/** 板块列表（含话题数） */
export async function listNodes() {
  const { data } = await request.get('/bbs/nodes/')
  return data.map(mapNode)
}

/** 话题列表 ?node=&sort=latest|replies&page= */
export async function listTopics({ node, sort, page = 1, pageSize = 20 } = {}) {
  const params = { page, page_size: pageSize }
  if (node) params.node = node
  if (sort) params.sort = sort
  const { data } = await request.get('/bbs/topics/', { params })
  return { list: (data.results || []).map(mapTopic), total: data.count || 0 }
}

export async function getTopic(id) {
  const { data } = await request.get(`/bbs/topics/${id}/`)
  return mapTopic(data)
}

/** 楼层列表（不含楼主帖） */
export async function listPosts(topicId, { page = 1, pageSize = 20 } = {}) {
  const { data } = await request.get(`/bbs/topics/${topicId}/posts/`, {
    params: { page, page_size: pageSize }
  })
  return { list: (data.results || []).map(mapPost), total: data.count || 0 }
}

export async function createTopic({ title, node, contentMd }) {
  const { data } = await request.post('/bbs/topics/', {
    title, node, content_md: contentMd
  })
  return mapTopic(data)
}

export async function createPost(topicId, contentMd) {
  const { data } = await request.post(`/bbs/topics/${topicId}/posts/`, {
    content_md: contentMd
  })
  return mapPost(data)
}

export async function toggleTopicLike(id) {
  const { data } = await request.post(`/bbs/topics/${id}/like/`)
  return data
}

export async function togglePostLike(topicId, postId) {
  const { data } = await request.post(`/bbs/topics/${topicId}/posts/${postId}/like/`)
  return data
}

/** 未登录跳 CMS 登录页（MVP 复用飞书 OAuth），登录后回到 BBS */
export function requireLogin(redirect) {
  if (isLoggedIn()) return true
  location.href = `/admin/login?redirect=${encodeURIComponent(redirect || location.pathname + location.search)}`
  return false
}

/** 相对时间：今天 HH:mm / 昨天 / MM-DD / YYYY-MM-DD */
export function formatForumTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const sameDay = (a, b) => a.toDateString() === b.toDateString()
  if (sameDay(d, now)) return `今天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (sameDay(d, yesterday)) return `昨天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (d.getFullYear() === now.getFullYear()) return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
