<template>
  <div class="bbs-wrap topic-page">
    <template v-if="topic">
      <!-- 面包屑 -->
      <div class="crumb">
        <router-link to="/bbs">论坛交流</router-link>
        <template v-if="topic.node">
          <span class="crumb-sep">/</span>
          <router-link :to="`/bbs/b/${topic.node.slug}`">{{ topic.node.name }}</router-link>
        </template>
      </div>

      <!-- 楼主帖 -->
      <div class="bbs-post-card">
        <div class="bbs-post-head">
          <img v-if="topic.author?.avatar" class="bbs-avatar" :src="topic.author.avatar" :alt="topic.author.name" />
          <span v-else class="bbs-avatar">{{ (topic.author?.name || '?').slice(0, 1) }}</span>
          <span class="author-name">{{ topic.author?.name }}</span>
          <span class="post-time">
            {{ formatForumTime(topic.createdAt) }}
            <span v-if="topic.editedAt" class="post-edited">· 已编辑 {{ formatForumTime(topic.editedAt) }}</span>
          </span>
          <span class="bbs-post-floor">1 楼</span>
        </div>

        <template v-if="!editingTopic">
          <h1 class="topic-title">
            <span v-if="topic.isPinned" class="bbs-badge pin">置顶</span>
            <span v-if="topic.isClosed" class="bbs-badge lock">锁定</span>
            {{ topic.title }}
          </h1>

          <div class="bbs-content" v-html="topic.contentHtml"></div>

          <div class="bbs-post-actions">
            <button
              class="bbs-like-btn"
              :class="{ liked: topic.liked }"
              @click="likeTopic"
            >👍 {{ topic.likeCount }}</button>
            <button v-if="!topic.isClosed" class="bbs-like-btn quote-btn" @click="quotePost(1, topic.author?.name, '')">引用</button>
            <button v-if="topic.canEdit" class="bbs-like-btn quote-btn" @click="startEditTopic">编辑</button>
            <button v-if="topic.canDelete" class="bbs-like-btn danger-btn" @click="removeTopic">删除</button>
            <span class="stat-view">{{ topic.viewCount }} 浏览</span>
          </div>
        </template>

        <!-- 话题编辑态 -->
        <div v-else class="topic-edit-box">
          <input v-model="editForm.title" class="topic-edit-title" maxlength="200" placeholder="标题（至少 6 个字）" />
          <MdEditor v-model="editForm.contentMd" :rows="10" />
          <div class="edit-actions">
            <button class="bbs-btn bbs-btn-primary" :disabled="savingTopic" @click="saveTopicEdit">
              {{ savingTopic ? '保存中…' : '保存修改' }}
            </button>
            <button class="bbs-btn bbs-btn-ghost" :disabled="savingTopic" @click="editingTopic = false">取消</button>
            <span class="edit-window-hint">发表 60 分钟内可编辑</span>
          </div>
        </div>
      </div>

      <!-- 楼层回复 -->
      <div v-if="posts.length === 0 && !loadingPosts" class="bbs-empty replies-empty">
        还没有回复，快来抢占 2 楼
      </div>
      <div v-for="p in posts" :key="p.id" class="bbs-post-card">
        <div class="bbs-post-head">
          <img v-if="p.author?.avatar" class="bbs-avatar" :src="p.author.avatar" :alt="p.author.name" />
          <span v-else class="bbs-avatar">{{ (p.author?.name || '?').slice(0, 1) }}</span>
          <span class="author-name">{{ p.author?.name }}</span>
          <span class="post-time">
            {{ formatForumTime(p.createdAt) }}
            <span v-if="p.editedAt" class="post-edited">· 已编辑 {{ formatForumTime(p.editedAt) }}</span>
          </span>
          <span class="bbs-post-floor">{{ p.floor }} 楼</span>
        </div>

        <!-- 已删除占位（软删除：楼层号保留，引用不悬空） -->
        <div v-if="p.deleted" class="bbs-content post-deleted">该回复已被作者删除</div>

        <!-- 编辑态 -->
        <div v-else-if="editingPostId === p.id" class="topic-edit-box">
          <MdEditor v-model="editPostMd" :rows="5" />
          <div class="edit-actions">
            <button class="bbs-btn bbs-btn-primary" :disabled="savingPost" @click="savePostEdit(p)">
              {{ savingPost ? '保存中…' : '保存修改' }}
            </button>
            <button class="bbs-btn bbs-btn-ghost" :disabled="savingPost" @click="editingPostId = null">取消</button>
          </div>
        </div>

        <template v-else>
          <div class="bbs-content" v-html="p.contentHtml"></div>
          <div class="bbs-post-actions">
            <button
              class="bbs-like-btn"
              :class="{ liked: p.liked }"
              @click="likePost(p)"
            >👍 {{ p.likeCount }}</button>
            <button v-if="!topic.isClosed" class="bbs-like-btn quote-btn" @click="quotePost(p.floor, p.author?.name, p.contentMd)">引用</button>
            <button v-if="p.canEdit" class="bbs-like-btn quote-btn" @click="startEditPost(p)">编辑</button>
            <button v-if="p.canDelete" class="bbs-like-btn danger-btn" @click="removePost(p)">删除</button>
          </div>
        </template>
      </div>

      <div class="bbs-loadmore" v-if="hasMorePosts">
        <button class="bbs-btn bbs-btn-ghost" :disabled="loadingPosts" @click="loadPosts">
          {{ loadingPosts ? '加载中…' : '加载更多回复' }}
        </button>
      </div>

      <!-- 回复框 -->
      <div class="reply-box">
        <template v-if="!topic.isClosed">
          <div class="reply-head">回复话题</div>
          <MdEditor
            ref="editorRef"
            v-model="replyMd"
            :rows="5"
            placeholder="友善交流，共同营造…（支持 Markdown）"
            @submit="submitReply"
          />
          <div class="reply-actions">
            <button
              class="bbs-btn bbs-btn-primary"
              :disabled="replying || !replyMd.trim()"
              @click="submitReply"
            >
              {{ replying ? '回复中…' : '回复' }}
            </button>
          </div>
        </template>
        <div v-else class="bbs-empty">话题已锁定，无法回复</div>
      </div>
    </template>

    <div v-else-if="loadingTopic" class="bbs-empty">加载中…</div>
    <div v-else class="bbs-empty">
      话题不存在
      <div style="margin-top: 14px">
        <router-link to="/bbs"><button class="bbs-btn bbs-btn-ghost">返回论坛</button></router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MdEditor from '@/components/bbs/MdEditor.vue'
import {
  getTopic,
  listPosts,
  createPost,
  toggleTopicLike,
  togglePostLike,
  updateMyTopic,
  deleteMyTopic,
  updateMyPost,
  deleteMyPost,
  formatForumTime,
  requireLogin
} from '@/api/bbs'

const props = defineProps({
  id: { type: String, required: true }
})
const route = useRoute()
const router = useRouter()

const topic = ref(null)
const posts = ref([])
const loadingTopic = ref(true)
const loadingPosts = ref(false)
const postPage = ref(1)
const hasMorePosts = ref(false)
const replyMd = ref('')
const replying = ref(false)
const editorRef = ref(null)

// ---- 作者自编辑/自删除 ----
const editingTopic = ref(false)
const editForm = reactive({ title: '', contentMd: '' })
const savingTopic = ref(false)
const editingPostId = ref(null)
const editPostMd = ref('')
const savingPost = ref(false)

function startEditTopic() {
  editForm.title = topic.value.title
  editForm.contentMd = topic.value.contentMd || ''
  editingTopic.value = true
}

async function saveTopicEdit() {
  if (editForm.title.trim().length < 6) {
    ElMessage.warning('标题至少 6 个字')
    return
  }
  savingTopic.value = true
  try {
    topic.value = await updateMyTopic(topic.value.id, {
      title: editForm.title.trim(),
      contentMd: editForm.contentMd
    })
    editingTopic.value = false
    document.title = `${topic.value.title} · 论坛交流`
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败，请重试')
  } finally {
    savingTopic.value = false
  }
}

function removeTopic() {
  ElMessageBox.confirm('确定删除这个话题？删除后不可恢复。', '删除确认', { type: 'warning' })
    .then(async () => {
      try {
        await deleteMyTopic(topic.value.id)
        ElMessage.success('已删除')
        router.push('/bbs')
      } catch (e) {
        ElMessage.error(e?.response?.data?.detail || '删除失败')
      }
    })
    .catch(() => {})
}

function startEditPost(p) {
  editingPostId.value = p.id
  editPostMd.value = p.contentMd
}

async function savePostEdit(p) {
  if (!editPostMd.value.trim()) {
    ElMessage.warning('回复内容不能为空')
    return
  }
  savingPost.value = true
  try {
    const updated = await updateMyPost(props.id, p.id, editPostMd.value.trim())
    const i = posts.value.findIndex((x) => x.id === p.id)
    if (i >= 0) posts.value[i] = updated
    editingPostId.value = null
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败，请重试')
  } finally {
    savingPost.value = false
  }
}

function removePost(p) {
  ElMessageBox.confirm('确定删除这条回复？删除后显示"已删除"占位。', '删除确认', { type: 'warning' })
    .then(async () => {
      try {
        await deleteMyPost(props.id, p.id)
        p.deleted = true
        p.contentHtml = ''
        p.contentMd = ''
        ElMessage.success('已删除')
      } catch (e) {
        ElMessage.error(e?.response?.data?.detail || '删除失败')
      }
    })
    .catch(() => {})
}

/**
 * 引用回复：把楼层内容截为 blockquote 插入回复框并聚焦。
 * 未登录时 MdEditor 内部会走 requireLogin 跳登录，这里不再重复判断。
 */
function quotePost(floor, name, contentMd) {
  const quoted = (contentMd || '')
    .split('\n')
    .slice(0, 3) // 最多引 3 行，防超长
    .map((l) => `> ${l}`)
    .join('\n')
  const head = `> **${name || '匿名'}**（${floor} 楼）\n${quoted}\n\n`
  replyMd.value = replyMd.value
    ? `${replyMd.value.replace(/\s*$/, '')}\n\n${head}`
    : head
  nextTick(() => {
    editorRef.value?.focus?.()
    editorRef.value?.$el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

async function loadTopic() {
  loadingTopic.value = true
  topic.value = null
  try {
    topic.value = await getTopic(props.id)
    document.title = `${topic.value.title} · 论坛交流`
  } catch {
    topic.value = null
  } finally {
    loadingTopic.value = false
  }
}

async function loadPosts(reset = false) {
  if (reset) {
    postPage.value = 1
    posts.value = []
  }
  loadingPosts.value = true
  try {
    const { list, total } = await listPosts(props.id, { page: postPage.value })
    posts.value = reset ? list : [...posts.value, ...list]
    hasMorePosts.value = posts.value.length < total
  } finally {
    loadingPosts.value = false
  }
}

async function submitReply() {
  if (replying.value || !replyMd.value.trim()) return
  if (!requireLogin(route.fullPath)) return
  replying.value = true
  try {
    const p = await createPost(props.id, replyMd.value.trim())
    posts.value.push(p)
    hasMorePosts.value = false // 尾部追加后无需再分页
    if (topic.value) {
      topic.value.replyCount += 1
      topic.value.lastReplyAt = new Date().toISOString()
    }
    replyMd.value = ''
    ElMessage.success('回复成功')
  } catch (e) {
    const detail = e?.response?.data
    ElMessage.error(detail?.content_md?.[0] || detail?.detail || (Array.isArray(detail) ? detail[0] : '回复失败，请重试'))
  } finally {
    replying.value = false
  }
}

async function likeTopic() {
  if (!requireLogin(route.fullPath)) return
  try {
    const r = await toggleTopicLike(topic.value.id)
    topic.value.liked = r.liked
    topic.value.likeCount = r.like_count
  } catch {
    ElMessage.error('操作失败，请重试')
  }
}

async function likePost(p) {
  if (!requireLogin(route.fullPath)) return
  try {
    const r = await togglePostLike(props.id, p.id)
    p.liked = r.liked
    p.likeCount = r.like_count
  } catch {
    ElMessage.error('操作失败，请重试')
  }
}

onMounted(() => {
  loadTopic()
  loadPosts(true)
})

watch(
  () => props.id,
  () => {
    if (route.path.startsWith('/bbs/t/')) {
      loadTopic()
      loadPosts(true)
    }
  }
)
</script>

<style scoped>
.topic-page {
  max-width: 820px;
}
.crumb {
  font-size: 13px;
  color: var(--text-light);
  margin-bottom: 12px;
}
.crumb a {
  color: var(--text-gray);
  text-decoration: none;
}
.crumb a:hover {
  color: var(--primary-green);
}
.crumb-sep {
  margin: 0 6px;
}
.topic-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 14px;
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.stat-view {
  font-size: 12px;
  color: var(--text-light);
  margin-left: auto;
}
.replies-empty {
  margin-bottom: 12px;
}
.reply-box {
  margin-top: 20px;
}
.reply-head {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-dark);
  margin-bottom: 10px;
}
.reply-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

/* ---- 作者自编辑/自删除 ---- */
.post-edited {
  color: var(--text-light);
  font-size: 12px;
}
.danger-btn:hover {
  color: #c0392b;
  border-color: #f2c4c0;
}
.post-deleted {
  color: var(--text-light);
  font-style: italic;
  background: #f6f7f5;
  border-radius: 6px;
  padding: 14px 16px;
  font-size: 13px;
}
.topic-edit-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.topic-edit-title {
  width: 100%;
  padding: 10px 14px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-dark);
  border: 1px solid #dce4dc;
  border-radius: 6px;
  outline: none;
}
.topic-edit-title:focus {
  border-color: var(--primary-green);
}
.edit-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.edit-window-hint {
  font-size: 12px;
  color: var(--text-light);
  margin-left: auto;
}
</style>
