<template>
  <div class="sitepage-wrap" v-loading="loading">
    <div
      v-if="page"
      class="sitepage"
      :class="`sitepage-${page.slug}`"
      v-html="page.content_html"
    ></div>
    <div v-else-if="!loading" class="sitepage-empty">
      <p>页面内容尚未配置</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getSitePage } from '@/api/sitepage'

const props = defineProps({
  slug: { type: String, required: true }
})

const loading = ref(true)
const page = ref(null)

async function load() {
  loading.value = true
  page.value = null
  const res = await getSitePage(props.slug)
  if (res.code === 0) {
    page.value = res.data
    if (page.value && page.value.title) {
      document.title = page.value.title
    }
  }
  loading.value = false
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
