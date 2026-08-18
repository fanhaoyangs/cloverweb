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
  const res = await listArticles({ section, pageSize: 8 })
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
