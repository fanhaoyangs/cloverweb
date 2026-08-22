<template>
  <div class="bbs-wrap">
    <div class="bbs-toolbar">
      <h1 class="bbs-title">论坛交流</h1>
      <div class="bbs-toolbar-actions">
        <span v-if="user" class="bbs-user">
          <img v-if="user.avatar" class="bbs-avatar sm" :src="user.avatar" :alt="user.name" />
          <span v-else class="bbs-avatar sm">{{ (user.name || '?').slice(0, 1) }}</span>
          {{ user.name }}
        </span>
        <button class="bbs-btn bbs-btn-primary" @click="goNew">发帖</button>
      </div>
    </div>

    <!-- 板块 pills（Flarum 式：全部 + 各板块） -->
    <div class="bbs-node-bar">
      <span
        class="bbs-node-pill"
        :class="{ active: !activeNode }"
        @click="switchNode('')"
      >全部</span>
      <span
        v-for="n in nodes"
        :key="n.slug"
        class="bbs-node-pill"
        :class="{ active: activeNode === n.slug }"
        @click="switchNode(n.slug)"
      >
        {{ n.icon }} {{ n.name }}
        <span class="pill-count">{{ n.topicCount }}</span>
      </span>
    </div>

    <!-- 话题列表 -->
    <div v-if="loading && topics.length === 0" class="bbs-empty">加载中…</div>
    <div v-else-if="topics.length === 0" class="bbs-empty">
      {{ activeNode ? '该板块还没有话题，来发第一帖吧' : '还没有话题，来发第一帖吧' }}
    </div>
    <div v-else class="bbs-list">
      <div
        v-for="t in topics"
        :key="t.id"
        class="bbs-topic-row"
        @click="$router.push(`/bbs/t/${t.id}`)"
      >
        <img v-if="t.author?.avatar" class="bbs-avatar" :src="t.author.avatar" :alt="t.author.name" />
        <span v-else class="bbs-avatar">{{ (t.author?.name || '?').slice(0, 1) }}</span>

        <div class="bbs-topic-main">
          <div class="bbs-topic-title-line">
            <span v-if="t.isPinned" class="bbs-badge pin">置顶</span>
            <span v-if="t.isClosed" class="bbs-badge lock">锁定</span>
            <span class="bbs-topic-title">{{ t.title }}</span>
          </div>
          <p v-if="t.excerpt" class="bbs-topic-excerpt">{{ t.excerpt }}</p>
          <div class="bbs-topic-meta">
            <span v-if="t.node" class="bbs-node-tag">{{ t.node.name }}</span>
            <span>{{ t.author?.name }}</span>
            <span>·</span>
            <span>{{ formatForumTime(t.lastReplyAt || t.createdAt) }}</span>
          </div>
        </div>

        <div class="bbs-topic-side">
          <span class="side-num"><b>{{ t.replyCount }}</b>回复</span>
          <span class="side-num"><b>{{ t.viewCount }}</b>浏览</span>
        </div>
      </div>
    </div>

    <div class="bbs-loadmore" v-if="hasMore">
      <button class="bbs-btn bbs-btn-ghost" :disabled="loading" @click="loadMore">
        {{ loading ? '加载中…' : '加载更多' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listNodes, listTopics, formatForumTime, requireLogin } from '@/api/bbs'
import { getUser } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const nodes = ref([])
const topics = ref([])
const loading = ref(false)
const page = ref(1)
const hasMore = ref(false)
const user = computed(() => getUser())

const activeNode = computed(() => route.params.node || '')

async function loadNodes() {
  try {
    nodes.value = await listNodes()
  } catch {
    nodes.value = []
  }
}

async function loadTopics(reset = false) {
  if (reset) {
    page.value = 1
    topics.value = []
  }
  loading.value = true
  try {
    const { list, total } = await listTopics({
      node: activeNode.value || undefined,
      page: page.value
    })
    topics.value = reset ? list : [...topics.value, ...list]
    hasMore.value = topics.value.length < total
  } finally {
    loading.value = false
  }
}

function loadMore() {
  page.value += 1
  loadTopics()
}

function switchNode(slug) {
  if (slug) {
    router.push(`/bbs/b/${slug}`)
  } else {
    router.push('/bbs')
  }
}

function goNew() {
  if (requireLogin('/bbs/new')) router.push('/bbs/new')
}

onMounted(() => {
  loadNodes()
  loadTopics(true)
})

// /bbs <-> /bbs/b/:node 同组件切换时重载
watch(activeNode, () => loadTopics(true))
</script>

<style scoped>
.bbs-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-gray);
}
.bbs-avatar.sm {
  width: 28px;
  height: 28px;
  font-size: 13px;
}
</style>
