<template>
  <div class="news-page">
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <h1 class="hero-title">资讯分享</h1>
        <p class="hero-subtitle">社区花园动态与活动资讯</p>
      </div>
    </section>

    <div class="category-filter">
      <div class="category-filter-inner">
        <div class="filter-links">
          <span
            v-for="tab in tabs"
            :key="tab.value"
            class="filter-link"
            :class="{ active: activeTab === tab.value }"
            @click="switchTab(tab.value)"
          >{{ tab.label }}</span>
        </div>
        <div class="search-box">
          <input
            type="text"
            class="search-input"
            v-model="searchKeyword"
            placeholder="搜索资讯..."
            @keyup.enter="handleSearch"
          />
          <button class="search-btn" @click="handleSearch">搜索</button>
        </div>
      </div>
    </div>

    <section class="posts-section">
      <div class="posts-grid">
        <div v-if="filteredList.length === 0 && !loading" class="empty-state">
          <div class="empty-state-icon">📭</div>
          <h3 class="empty-state-title">暂无资讯</h3>
          <p class="empty-state-text">当前分类下还没有发布文章，敬请期待！</p>
        </div>

        <div
          v-for="item in filteredList"
          :key="item.slug"
          class="post-card"
          :class="{ 'no-image': !item.coverImage }"
          @click="handleClick(item)"
        >
          <div v-if="item.coverImage" class="post-card-image-wrapper">
            <img class="post-card-image" :src="item.coverImage" :alt="item.title" />
            <span class="post-card-category">{{ item.categoryLabel }}</span>
          </div>
          <div class="post-card-content">
            <h3 class="post-card-title">{{ item.title }}</h3>
            <p v-if="item.excerpt" class="post-card-excerpt">{{ item.excerpt }}</p>
            <div class="post-card-meta">
              <span class="post-card-date">{{ formatDate(item.sortTime) }}</span>
              <span v-if="item.externalUrl" class="post-card-link">查看详情 →</span>
            </div>
          </div>
        </div>
      </div>

      <div class="pagination" v-if="hasMore">
        <button class="load-more-btn" @click="loadMore" :disabled="loading">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listArticles, CATEGORIES } from '@/api/article'

const router = useRouter()

const loading = ref(false)
const articles = ref([])
const activeTab = ref('all')
const searchKeyword = ref('')
const articlePage = ref(1)
const hasMore = ref(false)

const tabs = computed(() => {
  const base = [{ value: 'all', label: '全部' }]
  const cats = CATEGORIES.map(c => ({ value: c.value, label: c.label }))
  return [...base, ...cats]
})

const filteredList = computed(() => {
  let list = [...articles.value]

  if (activeTab.value !== 'all') {
    list = list.filter(i => i.category === activeTab.value)
  }

  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(i =>
      (i.title && i.title.toLowerCase().includes(kw)) ||
      (i.excerpt && i.excerpt.toLowerCase().includes(kw))
    )
  }

  list.sort((a, b) => new Date(b.publishedAt || 0) - new Date(a.publishedAt || 0))
  return list
})

function switchTab(tab) {
  activeTab.value = tab
}

function handleSearch() {
}

function handleClick(item) {
  router.push(`/news/${item.slug}`)
}

async function loadArticles() {
  loading.value = true
  try {
    const res = await listArticles({ page: articlePage.value, pageSize: 20 })
    console.log('listArticles response:', res)
    if (res.code === 0) {
      if (articlePage.value === 1) {
        articles.value = res.data.list
      } else {
        articles.value.push(...res.data.list)
      }
      hasMore.value = articles.value.length < res.data.total
      console.log('articles loaded:', articles.value.length, 'total:', res.data.total)
    } else {
      console.error('listArticles error:', res.message)
    }
  } catch (e) {
    console.error('加载文章失败', e)
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  articlePage.value++
  await loadArticles()
}

function formatDate(value) {
  if (!value) return ''
  const d = new Date(value)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

onMounted(() => {
  loadArticles()
})
</script>

<style scoped>
.hero {
  position: relative;
  height: 50vh;
  min-height: 450px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(135deg, var(--primary-green) 0%, var(--primary-green-dark) 100%);
}

.hero-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('https://images.communitygarden.org.cn/communitygarden/资讯分享头图.jpg') center center/cover no-repeat;
  opacity: 0.3;
}

.hero-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(90, 125, 90, 0.4);
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: var(--white);
  max-width: 800px;
  padding: 0 40px;
  transform: translateY(10px);
}

.hero-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 48px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: 4px;
  margin-bottom: 20px;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.hero-subtitle {
  font-size: 16px;
  font-weight: 300;
  letter-spacing: 2px;
  opacity: 0.9;
}

.category-filter {
  background: var(--white);
  padding: 30px 0;
  box-shadow: 0 2px 15px var(--shadow);
  position: sticky;
  top: 70px;
  z-index: 100;
}

.category-filter-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 60px;
  display: flex;
  align-items: center;
  gap: 30px;
  flex-wrap: wrap;
}

.filter-links {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.filter-link {
  padding: 8px 20px;
  background: var(--bg-cream);
  color: var(--text-gray);
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.filter-link:hover,
.filter-link.active {
  background: var(--primary-green);
  color: var(--white);
}

.search-box {
  margin-left: auto;
  display: flex;
  gap: 10px;
}

.search-input {
  padding: 10px 20px;
  border: 2px solid var(--bg-cream);
  border-radius: 25px;
  font-size: 14px;
  color: var(--text-dark);
  width: 250px;
  outline: none;
  transition: border-color 0.3s ease;
  background: var(--white);
}

.search-input:focus {
  border-color: var(--primary-green);
}

.search-btn {
  padding: 10px 25px;
  background: var(--primary-green);
  color: var(--white);
  border: none;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
}

.search-btn:hover {
  background: var(--primary-green-dark);
}

.posts-section {
  background: var(--bg-light);
  padding: 60px;
}

.posts-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 30px;
}

.post-card {
  background: var(--white);
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 15px var(--shadow);
  transition: all 0.4s ease;
  cursor: pointer;
  display: block;
}

.post-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 30px rgba(90, 125, 90, 0.2);
}

.post-card-image-wrapper {
  overflow: hidden;
  position: relative;
}

.post-card-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  transition: transform 0.4s ease;
  display: block;
}

.post-card:hover .post-card-image {
  transform: scale(1.05);
}

.post-card-category {
  position: absolute;
  top: 15px;
  left: 15px;
  padding: 6px 15px;
  background: var(--primary-green);
  color: var(--white);
  font-size: 12px;
  border-radius: 15px;
  z-index: 2;
}

.post-card-content {
  padding: 25px;
}

.post-card-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-dark);
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-card:hover .post-card-title {
  color: var(--primary-green);
}

.post-card-excerpt {
  font-size: 13px;
  color: var(--text-gray);
  line-height: 1.8;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 15px;
}

.post-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 15px;
  border-top: 1px solid var(--bg-cream);
}

.post-card-date {
  font-size: 12px;
  color: var(--text-light);
}

.post-card-link {
  font-size: 12px;
  color: var(--primary-green);
  font-weight: 500;
}

.post-card.no-image .post-card-content {
  padding-top: 25px;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 80px 40px;
}

.empty-state-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.empty-state-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 24px;
  color: var(--text-dark);
  margin-bottom: 15px;
}

.empty-state-text {
  font-size: 14px;
  color: var(--text-gray);
  margin-bottom: 30px;
}

.pagination {
  text-align: center;
  margin-top: 40px;
}

.load-more-btn {
  padding: 12px 40px;
  background: var(--primary-green);
  color: var(--white);
  border: none;
  border-radius: 25px;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.load-more-btn:hover {
  background: var(--primary-green-dark);
}

.load-more-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 1100px) {
  .posts-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .category-filter-inner {
    padding: 0 40px;
  }

  .posts-section {
    padding: 50px 40px;
  }
}

@media (max-width: 768px) {
  .hero {
    height: 25vh;
    min-height: 250px;
  }

  .hero-title {
    font-size: 32px;
    letter-spacing: 2px;
  }

  .hero-subtitle {
    font-size: 14px;
  }

  .posts-grid {
    grid-template-columns: 1fr;
  }

  .category-filter-inner {
    flex-direction: column;
    align-items: flex-start;
    padding: 0 20px;
  }

  .search-box {
    width: 100%;
    margin-left: 0;
  }

  .search-input {
    flex: 1;
    width: auto;
  }

  .posts-section {
    padding: 40px 20px;
  }
}
</style>
