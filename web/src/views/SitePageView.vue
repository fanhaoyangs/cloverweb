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

async function load() {
  loading.value = true
  page.value = null
  const res = await getSitePage(props.slug)
  if (res.code === 0) {
    page.value = res.data
    if (page.value && page.value.title) {
      document.title = page.value.title
    }
    if (props.slug === 'home') {
      await nextTick()
      injectHomeNews()
    }
  }
  loading.value = false
}

/**
 * 首页资讯卡片接线：把 section=home_news 的已发布文章卡片
 * 前插到静态 HTML 的「新闻回顾」网格（.review-grid），复用原卡片样式。
 */
async function injectHomeNews() {
  const grid = pageEl.value?.querySelector('.review-grid')
  if (!grid) return

  const res = await listArticles({ websiteSection: 'home_news', pageSize: 4 })
  if (res.code !== 0) return
  const articles = res.data.list || []
  if (articles.length === 0) return

  const frag = document.createDocumentFragment()
  for (const a of articles) {
    const link = document.createElement('a')
    link.href = `/news/${a.slug}`
    link.className = 'review-card-link'
    link.innerHTML = `
      <div class="review-card">
        <div class="review-image">
          <img src="${a.coverImage || 'https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png'}" alt="${escapeHtml(a.title)}" loading="lazy">
        </div>
        <div class="review-content-area">
          <p>${escapeHtml(a.title)}</p>
        </div>
      </div>`
    frag.appendChild(link)
  }
  grid.insertBefore(frag, grid.firstChild)
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
