<template>
  <div class="sitepage-wrap" v-loading="loading">
    <div
      v-if="page"
      class="sitepage"
      :class="`sitepage-${page.slug}`"
      v-html="page.content_html"
      ref="pageEl"
    ></div>
    <div v-else-if="!loading" class="sitepage-empty">
      <template v-if="notFound">
        <p class="nf-code">404</p>
        <p class="nf-text">页面不存在或已下线</p>
        <router-link to="/" class="nf-link">返回首页</router-link>
      </template>
      <p v-else>页面内容尚未配置</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { getSitePage } from '@/api/sitepage'
import { listArticles } from '@/api/article'

const props = defineProps({
  slug: { type: String, required: true }
})

const loading = ref(true)
const page = ref(null)
const pageEl = ref(null)
const notFound = ref(false)

/**
 * 卡片模板库：静态页 HTML 中 <div data-article-block="板块" data-card="模板" data-limit="N">
 * data-card 可选：review / media / publication / case / salon（缺省 review）
 */
const CARD_TEMPLATES = {
  review: (a) => `
    <a href="/news/${a.slug}" class="review-card-link">
      <div class="review-card">
        <div class="review-image">
          <img src="${escapeHtml(a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png')}" alt="${escapeHtml(a.title)}" loading="lazy">
        </div>
        <div class="review-content-area">
          <p>${escapeHtml(a.title)}</p>
        </div>
      </div>
    </a>`,
  media: (a) => `
    <a href="/news/${a.slug}" class="media-card-link">
      <div class="media-card">
        <div class="media-image">
          <img src="${escapeHtml(a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png')}" alt="${escapeHtml(a.title)}" loading="lazy">
        </div>
        <div class="media-content-area">
          <h4>${escapeHtml(a.title)}</h4>
          ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
        </div>
      </div>
    </a>`,
  publication: (a) => `
    <a href="/news/${a.slug}" class="publication-card-link">
      <div class="publication-card">
        <div class="publication-image">
          <img src="${escapeHtml(a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png')}" alt="${escapeHtml(a.title)}" loading="lazy">
        </div>
        <div class="publication-content-area">
          <h4>${escapeHtml(a.title)}</h4>
          ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
        </div>
      </div>
    </a>`,
  case: (a) => `
    <a href="/news/${a.slug}" class="case-card-link">
      <div class="case-card">
        <div class="case-image">
          <img src="${escapeHtml(a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png')}" alt="${escapeHtml(a.title)}" loading="lazy">
        </div>
        <div class="case-content-area">
          <h4>${escapeHtml(a.title)}</h4>
          ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
        </div>
      </div>
    </a>`,
  salon: (a) => `
    <a href="/news/${a.slug}" class="salon-card-link">
      <h4>${escapeHtml(a.title)}</h4>
      ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
      <span class="salon-link">了解详情 →</span>
    </a>`
}

/**
 * 旧式兼容配置：页面 HTML 里若没有 data-article-block 占位符，
 * 则按此处 selector 回退注入（现有静态页仍生效）。
 */
const SECTION_INJECTIONS = {
  home: [
    { selector: '.review-grid', section: 'home_news', prepend: true, card: 'review' }
  ],
  clover: [
    { selector: '.media-grid', section: 'clover_media', prepend: true, card: 'media' }
  ],
  philosophy: [
    { selector: '.salon-content', section: 'philosophy_salon', prepend: true, card: 'salon' },
    { selector: '.publications-grid', section: 'philosophy_publications', prepend: true, card: 'publication' },
    { selector: '.cases-grid', section: 'philosophy_cases', prepend: true, card: 'case' }
  ]
}

async function load() {
  loading.value = true
  page.value = null
  notFound.value = false
  document.title = '四叶草堂'
  const res = await getSitePage(props.slug)
  if (res.code === 0) {
    page.value = res.data
    if (page.value && page.value.title) {
      document.title = page.value.title
    }
    await nextTick()
    await injectAllSections()
  } else if (res.code === 404) {
    notFound.value = true
  }
  loading.value = false
}

/**
 * 注入文章块：
 * 1) 优先扫描页面里的 [data-article-block] 占位符（新方式，任意页面任意位置可用）
 * 2) 无占位符时回退到 SECTION_INJECTIONS 旧选择器（兼容现有页面）
 */
async function injectAllSections() {
  const placeholders = collectPlaceholders()
  let jobs = []
  if (placeholders.length) {
    jobs = placeholders.map((p) => () => injectIntoElement(p))
  } else {
    const injections = SECTION_INJECTIONS[props.slug] || []
    jobs = injections.map((cfg) => () => injectOne(cfg))
  }
  await Promise.all(
    jobs.map((fn) => fn().catch((e) => console.warn('[sitepage] inject 失败:', e)))
  )
}

// 扫描静态页 HTML 中的文章块占位符
function collectPlaceholders() {
  const blocks = pageEl.value?.querySelectorAll('[data-article-block]') || []
  const list = []
  blocks.forEach((el) => {
    const prependAttr = el.getAttribute('data-prepend') || 'true'
    list.push({
      el,
      section: (el.getAttribute('data-article-block') || '').trim(),
      card: el.getAttribute('data-card') || 'review',
      limit: parseInt(el.getAttribute('data-limit') || '8', 10) || 8,
      prepend: prependAttr === 'replace' ? 'replace' : (prependAttr === 'true')
    })
  })
  return list.filter((p) => p.section)
}

// 注入单个容器元素
async function injectIntoElement({ el, section, card, limit, prepend }) {
  if (!el || !section) return
  const res = await listArticles({ websiteSection: section, pageSize: limit })
  if (res.code !== 0) return
  const articles = res.data.list || []
  if (articles.length === 0) return
  const tpl = CARD_TEMPLATES[card] || CARD_TEMPLATES.review
  const wrapper = document.createElement('div')
  wrapper.innerHTML = articles.map(tpl).join('')
  const frag = document.createDocumentFragment()
  while (wrapper.firstChild) frag.appendChild(wrapper.firstChild)
  if (prepend === 'replace') {
    el.innerHTML = ''
    el.appendChild(frag)
  } else if (prepend === true) {
    el.insertBefore(frag, el.firstChild)
  } else {
    el.appendChild(frag)
  }
}

// 旧式注入：按 selector 找容器，复用 injectIntoElement
async function injectOne({ selector, section, prepend, card = 'review' }) {
  const container = pageEl.value?.querySelector(selector)
  if (!container) return
  await injectIntoElement({ el: container, section, card, limit: 8, prepend })
}

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]))
}

onMounted(load)
watch(() => props.slug, load)
</script>

<style scoped>
.sitepage-wrap {
  min-height: 60vh;
}

.sitepage-empty {
  padding: 100px 20px;
  text-align: center;
  color: #8a9a8a;
  font-size: 15px;
  letter-spacing: 2px;
}

/* 404：页面不存在或已下线 */
.nf-code {
  font-family: 'Noto Serif SC', serif;
  font-size: 72px;
  font-weight: 700;
  color: #5a7d5a;
  margin: 0 0 8px;
  letter-spacing: 6px;
}

.nf-text {
  margin: 0 0 28px;
}

.nf-link {
  display: inline-block;
  padding: 10px 32px;
  background: #5a7d5a;
  color: #fff;
  border-radius: 24px;
  text-decoration: none;
  font-size: 14px;
  transition: background 0.3s ease;
}

.nf-link:hover {
  background: #476347;
}
</style>

<!-- inject 卡片样式：v-html 内容不受 scoped 影响，用全局 -->
<style>
/* 通用：injected card 链接重置 */
.sitepage a.review-card-link,
.sitepage a.media-card-link,
.sitepage a.publication-card-link,
.sitepage a.case-card-link,
.sitepage a.salon-card-link {
  display: block;
  text-decoration: none;
  color: inherit;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border-radius: 10px;
  overflow: hidden;
}
.sitepage a.review-card-link:hover,
.sitepage a.media-card-link:hover,
.sitepage a.publication-card-link:hover,
.sitepage a.case-card-link:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

/* review-card / media-card / publication-card / case-card 卡片本身 */
.sitepage .review-card,
.sitepage .media-card,
.sitepage .publication-card,
.sitepage .case-card {
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  height: 100%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.sitepage .review-card img,
.sitepage .media-card img,
.sitepage .publication-card img,
.sitepage .case-card img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  display: block;
}
.sitepage .review-content-area,
.sitepage .media-content-area,
.sitepage .publication-content-area,
.sitepage .case-content-area {
  padding: 14px 16px 18px;
}
.sitepage .review-content-area p,
.sitepage .media-content-area h4,
.sitepage .publication-content-area h4,
.sitepage .case-content-area h4 {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.6;
  color: #3a3a3a;
  margin: 0 0 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.sitepage .media-content-area p,
.sitepage .publication-content-area p,
.sitepage .case-content-area p {
  font-size: 12px;
  color: #888;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* salon 单卡片（philosophy 路径里） */
.sitepage a.salon-card-link {
  display: block;
  padding: 30px 40px;
  background: #fff;
  border-left: 4px solid #5a7d5a;
  border-radius: 8px;
  margin-bottom: 20px;
}
.sitepage a.salon-card-link h4 {
  font-size: 18px;
  color: #2a3a2a;
  margin: 0 0 10px;
  font-weight: 500;
}
.sitepage a.salon-card-link p {
  font-size: 13px;
  color: #666;
  line-height: 1.8;
  margin: 0 0 12px;
}
.sitepage a.salon-card-link .salon-link {
  display: inline-block;
  font-size: 13px;
  color: #5a7d5a;
  font-weight: 500;
}

/* responsive */
@media (max-width: 768px) {
  .sitepage a.salon-card-link {
    padding: 20px;
  }
}
</style>
