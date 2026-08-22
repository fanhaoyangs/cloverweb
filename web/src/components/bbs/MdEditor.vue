<template>
  <div class="md-editor">
    <div class="md-toolbar">
      <button type="button" class="md-tool" title="加粗" @click="wrap('**', '**')">B</button>
      <button type="button" class="md-tool" title="斜体" @click="wrap('*', '*')"><i>I</i></button>
      <button type="button" class="md-tool" title="删除线" @click="wrap('~~', '~~')"><s>S</s></button>
      <button type="button" class="md-tool" title="引用" @click="prefixLine('> ')">❝</button>
      <button type="button" class="md-tool" title="行内代码" @click="wrap('`', '`')">&lt;&gt;</button>
      <button type="button" class="md-tool" title="代码块" @click="insert('\n```\n\n```\n')">```</button>
      <button type="button" class="md-tool" title="链接" @click="insertLink">🔗</button>
      <button type="button" class="md-tool" title="图片" @click="pickImage">🖼</button>
      <span class="md-hint">支持 Markdown · Ctrl+Enter 提交</span>
    </div>
    <textarea
      ref="taRef"
      class="md-textarea"
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      @input="$emit('update:modelValue', $event.target.value)"
      @keydown="onKeydown"
    ></textarea>
    <input ref="fileRef" type="file" accept="image/*" hidden @change="onFileChange" />
    <div v-if="uploading" class="md-uploading">图片上传中…</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import request from '@/utils/request'

defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '写下你的内容…' },
  rows: { type: Number, default: 10 }
})
const emit = defineEmits(['update:modelValue', 'submit'])

const taRef = ref(null)
const fileRef = ref(null)
const uploading = ref(false)

/** 在光标处插入文本 */
function insert(text) {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, selectionEnd: e, value } = ta
  const next = value.slice(0, s) + text + value.slice(e)
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    ta.focus()
    ta.selectionStart = ta.selectionEnd = s + text.length
  })
}

/** 用前后缀包裹选中文本 */
function wrap(before, after = before) {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, selectionEnd: e, value } = ta
  const selected = value.slice(s, e) || '文字'
  const next = value.slice(0, s) + before + selected + after + value.slice(e)
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    ta.focus()
    ta.selectionStart = s + before.length
    ta.selectionEnd = s + before.length + selected.length
  })
}

/** 行首加前缀（引用等） */
function prefixLine(prefix) {
  const ta = taRef.value
  if (!ta) return
  const { selectionStart: s, value } = ta
  const lineStart = value.lastIndexOf('\n', s - 1) + 1
  const next = value.slice(0, lineStart) + prefix + value.slice(lineStart)
  emit('update:modelValue', next)
  requestAnimationFrame(() => {
    ta.focus()
    ta.selectionStart = ta.selectionEnd = s + prefix.length
  })
}

function insertLink() {
  const url = prompt('链接地址（https://…）')
  if (!url) return
  const ta = taRef.value
  const selected = ta ? ta.value.slice(ta.selectionStart, ta.selectionEnd) : ''
  insert(`[${selected || '链接文字'}](${url})`)
}

function pickImage() {
  fileRef.value?.click()
}

/** 上传复用 UEditorPlus 的 COS 通道（/api/ueditor/?action=uploadimage） */
async function onFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('upfile', file)
    const { data } = await request.post('/ueditor/?action=uploadimage', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (data?.state === 'SUCCESS' && data.url) {
      insert(`\n![${file.name.replace(/\.[^.]+$/, '')}](${data.url})\n`)
    } else {
      alert(data?.message || '图片上传失败')
    }
  } catch {
    alert('图片上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    emit('submit')
  }
}
</script>

<style scoped>
.md-editor {
  border: 1px solid #dce4dc;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}
.md-editor:focus-within {
  border-color: var(--primary-green);
}
.md-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  border-bottom: 1px solid #eef2ee;
  background: #fafbfa;
  flex-wrap: wrap;
}
.md-tool {
  min-width: 30px;
  height: 28px;
  border: none;
  background: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-gray);
}
.md-tool:hover {
  background: #eef4ee;
  color: var(--primary-green);
}
.md-hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-light);
}
.md-textarea {
  display: block;
  width: 100%;
  border: none;
  outline: none;
  resize: vertical;
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.8;
  font-family: inherit;
  color: var(--text-dark);
}
.md-uploading {
  padding: 6px 14px;
  font-size: 12px;
  color: var(--primary-green);
  background: #f7faf7;
}
</style>
