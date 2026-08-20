<template>
  <div class="html-code-editor">
    <div ref="editorHost" class="editor-host" :style="{ height: height + 'px' }"></div>
    <div class="editor-statusbar">
      <span>行 {{ lineCount }}</span>
      <span>列 {{ col }}</span>
      <span>字符 {{ charCount }}</span>
      <span class="statusbar-spacer"></span>
      <span class="statusbar-lang">HTML</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection, rectangularSelection } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { html } from '@codemirror/lang-html'
import { indentWithTab, defaultKeymap, history, historyKeymap, undo, redo } from '@codemirror/commands'
import {
  syntaxHighlighting, defaultHighlightStyle, bracketMatching,
  indentOnInput, foldGutter, foldKeymap
} from '@codemirror/language'

const props = defineProps({
  modelValue: { type: String, default: '' },
  height: { type: Number, default: 480 }
})

const emit = defineEmits(['update:modelValue'])

const editorHost = ref(null)
const view = ref(null)

const lineCount = ref(0)
const col = ref(0)
const charCount = ref(0)

function syncCursor(state) {
  const head = state.selection.main.head
  const line = state.doc.lineAt(head)
  lineCount.value = state.doc.lines
  charCount.value = state.doc.length
  col.value = head - line.from + 1
}

function buildState(content) {
  return EditorState.create({
    doc: content,
    extensions: [
      lineNumbers(),
      highlightActiveLine(),
      drawSelection(),
      rectangularSelection(),
      bracketMatching(),
      indentOnInput(),
      foldGutter(),
      html({ autoCloseTags: true, matchClosingTags: true }),
      syntaxHighlighting(defaultHighlightStyle),
      history(),
      keymap.of([
        indentWithTab,
        ...defaultKeymap,
        ...historyKeymap,
        ...foldKeymap
      ]),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          emit('update:modelValue', update.state.doc.toString())
        }
        syncCursor(update.state)
      })
    ]
  })
}

onMounted(() => {
  view.value = new EditorView({
    state: buildState(props.modelValue),
    parent: editorHost.value
  })
  syncCursor(view.value.state)
})

onBeforeUnmount(() => {
  view.value?.destroy()
  view.value = null
})

// 外部赋值（如切换页面/加载）时同步进编辑器
watch(() => props.modelValue, (val) => {
  if (!view.value) return
  const current = view.value.state.doc.toString()
  if (val !== current) {
    view.value.dispatch({
      changes: { from: 0, to: current.length, insert: val || '' }
    })
  }
})

defineExpose({
  focus: () => view.value?.focus(),
  undo: () => view.value && undo(view.value),
  redo: () => view.value && redo(view.value),
  insertSnippet: (text) => {
    if (!view.value) return
    const { from, to } = view.value.state.selection.main
    view.value.dispatch({
      changes: { from, to, insert: text },
      selection: { anchor: from + text.length }
    })
    view.value.focus()
  }
})
</script>

<style scoped>
.html-code-editor {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.editor-host {
  overflow: auto;
  text-align: left;
}

.editor-host :deep(.cm-editor) {
  height: 100%;
}

.editor-host :deep(.cm-scroller) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
}

.editor-statusbar {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 4px 12px;
  font-size: 12px;
  color: #8a9a8a;
  background: #f6f8f6;
  border-top: 1px solid #eef2ee;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
}

.statusbar-spacer {
  flex: 1;
}

.statusbar-lang {
  color: #5a7d5a;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}
</style>
