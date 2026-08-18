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
      <p>页面内容尚未配置</p>
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

/**
 * 每个 SitePage 里的"文章块"挂载配置。
 * selector: 容器 CSS 选择器（已存在静态页 HTML 里）
 * section:  Article.website_sections 的标记值
 * cardTpl:  注入卡片的 HTML 模板（标题 + 封面 + 链接）
 * prepend:  true=插入到容器最前，false=追加到末尾，'replace'=清空容器
 */
const SECTION_INJECTIONS = {
  home: [
    {
      selector: '.review-grid',
      section: 'home_news',
      prepend: true,
      cardTpl: (a) => `
        <a href="/news/${a.slug}" class="review-card-link">
          <div class="review-card">
            <div class="review-image">
              <img src="${a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png'}" alt="${escapeHtml(a.title)}" loading="lazy">
            </div>
            <div class="review-content-area">
              <p>${escapeHtml(a.title)}</p>
            </div>
          </div>
        </a>`
    }
  ],
  clover: [
    {
      selector: '.media-grid',
      section: 'clover_media',
      prepend: true,
      cardTpl: (a) => `
        <a href="/news/${a.slug}" class="media-card-link">
          <div class="media-card">
            <div class="media-image">
              <img src="${a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png'}" alt="${escapeHtml(a.title)}" loading="lazy">
            </div>
            <div class="media-content-area">
              <h4>${escapeHtml(a.title)}</h4>
              ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
            </div>
          </div>
        </a>`
    }
  ],
  philosophy: [
    {
      selector: '.salon-content',
      section: 'philosophy_salon',
      prepend: true,
      cardTpl: (a) => `
        <a href="/news/${a.slug}" class="salon-card-link">
          <h4>${escapeHtml(a.title)}</h4>
          ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
          <span class="salon-link">了解详情 →</span>
        </a>`
    },
    {
      selector: '.publications-grid',
      section: 'philosophy_publications',
      prepend: true,
      cardTpl: (a) => `
        <a href="/news/${a.slug}" class="publication-card-link">
          <div class="publication-card">
            <div class="publication-image">
              <img src="${a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png'}" alt="${escapeHtml(a.title)}" loading="lazy">
            </div>
            <div class="publication-content-area">
              <h4>${escapeHtml(a.title)}</h4>
              ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
            </div>
          </div>
        </a>`
    },
    {
      selector: '.cases-grid',
      section: 'philosophy_cases',
      prepend: true,
      cardTpl: (a) => `
        <a href="/news/${a.slug}" class="case-card-link">
          <div class="case-card">
            <div class="case-image">
              <img src="${a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png'}" alt="${escapeHtml(a.title)}" loading="lazy">
            </div>
            <div class="case-content-area">
              <h4>${escapeHtml(a.title)}</h4>
              ${a.excerpt ? `<p>${escapeHtml(a.excerpt)}</p>` : ''}
            </div>
          </div>
        </a>`
    }
  ]
}

async function load() {
  loading.value = true
  page.value = null
  const res = await getSitePage(props.slug)
  if (res.code === 0) {
    page.value = res.data
    if (page.value && page.value.title) {
      document.title = page.value.title
    }
    await nextTick()
    await injectAllSections()
  }
  loading.value = false
}

/**
 * 把每个 page 里配置的所有 article-block 容器注入 Article 卡片
 * 全部失败不抛错（用 try/catch 包住，缺某个 section selector 也不影响其他）
 */
async function injectAllSections() {
  const injections = SECTION_INJECTIONS[props.slug] || []
  for (const cfg of injections) {
    try {
      await injectOne(cfg)
    } catch (e) {
      console.warn(`[sitepage] inject 失败 ${cfg.section}:`, e)
    }
  }
}

async function injectOne({ selector, section, prepend, cardTpl }) {
  const container = pageEl.value?.querySelector(selector)
  if (!container) return
  const res = await listArticles({ websiteSection: section, pageSize: 8 })
  if (res.code !== 0) return
  const articles = res.data.list || []
  if (articles.length === 0) return
  const frag = document.createDocumentFragment()
  // 用 div 包裹避免 <a> 直接放进 fragment 报错
  const wrapper = document.createElement('div')
  wrapper.innerHTML = articles.map(cardTpl).join('')
  while (wrapper.firstChild) frag.appendChild(wrapper.firstChild)
  if (prepend === true) {
    container.insertBefore(frag, container.firstChild)
  } else if (prepend === 'replace') {
    container.innerHTML = ''
    container.appendChild(frag)
  } else {
    container.appendChild(frag)
  }
}

function escapeHtml(s) {
  const div = document.createElement('div')
  div.textContent = s || ''
  return div.innerHTML
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
