<template>
  <div class="article-detail-page">
    <div v-loading="loading" class="article-container">
      <template v-if="article">
        <div class="article-header">
          <div class="article-meta">
            <span class="article-category">{{ getCategoryLabel(article.category) }}</span>
            <span class="article-date">{{ formatDate(article.publishedAt) }}</span>
            <span v-if="article.author" class="article-author">{{ article.author }}</span>
          </div>
          <h1 class="article-title">{{ article.title }}</h1>
        </div>

        <div v-if="article.coverImage" class="article-cover">
          <img :src="article.coverImage" :alt="article.title" />
        </div>

        <div class="article-content" v-html="article.content"></div>

        <div v-if="article.galleryImages && article.galleryImages.length > 0" class="article-gallery">
          <h3>图片集</h3>
          <div class="gallery-grid">
            <el-image
              v-for="(img, index) in article.galleryImages"
              :key="index"
              :src="img"
              fit="cover"
              class="gallery-item"
              :preview-src-list="article.galleryImages"
              :initial-index="index"
            />
          </div>
        </div>

        <div class="article-footer">
          <el-button @click="$router.back()">返回列表</el-button>
        </div>
      </template>

      <div v-if="!loading && !article" class="not-found">
        <p>文章不存在或已被删除</p>
        <el-button @click="$router.push('/news')">返回资讯列表</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getArticleById, incrementView, getCategoryLabel } from '@/api/article'

const route = useRoute()
const loading = ref(true)
const article = ref(null)

function formatDate(timestamp) {
  if (!timestamp) return ''
  const d = new Date(timestamp)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

async function loadArticle() {
  loading.value = true
  try {
    const res = await getArticleById(route.params.id)
    if (res.code === 0 && res.data) {
      article.value = res.data
      incrementView(route.params.id).catch(() => {})
    }
  } catch (e) {
    console.error('加载文章失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadArticle()
})
</script>

<style scoped>
.article-detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
}

.article-container {
  min-height: 400px;
}

.article-header {
  margin-bottom: 24px;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.article-category {
  font-size: 13px;
  color: #5a7d5a;
  background: #e8f0e8;
  padding: 2px 10px;
  border-radius: 4px;
}

.article-date {
  font-size: 13px;
  color: #999;
}

.article-author {
  font-size: 13px;
  color: #999;
}

.article-title {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  line-height: 1.4;
}

.article-cover {
  margin-bottom: 24px;
  border-radius: 8px;
  overflow: hidden;
}

.article-cover img {
  width: 100%;
  display: block;
}

.article-content {
  font-size: 16px;
  line-height: 1.8;
  color: #333;
  word-break: break-word;
}

.article-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 16px 0;
}

.article-content :deep(p) {
  margin-bottom: 16px;
}

.article-content :deep(h1),
.article-content :deep(h2),
.article-content :deep(h3) {
  margin: 24px 0 12px;
  font-weight: 600;
}

.article-gallery {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.article-gallery h3 {
  font-size: 18px;
  margin-bottom: 16px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.gallery-item {
  width: 100%;
  height: 150px;
  border-radius: 4px;
  cursor: pointer;
}

.article-footer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  text-align: center;
}

.not-found {
  text-align: center;
  padding: 60px 0;
  color: #999;
}

.not-found p {
  font-size: 16px;
  margin-bottom: 20px;
}
</style>
