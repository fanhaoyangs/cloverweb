<template>
  <UEditor
    ref="ueditorRef"
    :modelValue="modelValue"
    @update:modelValue="handleInput"
    :height="height"
    :config="editorConfig"
  />
</template>

<script setup>
import { ref, computed } from 'vue'
import UEditor from './UEditor.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  height: { type: Number, default: 500 },
  imageUploadDir: { type: String, default: 'articles' },
  placeholder: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const ueditorRef = ref(null)

const editorConfig = computed(() => ({}))

function handleInput(val) {
  emit('update:modelValue', val)
}

defineExpose({
  getContent: () => ueditorRef.value?.getContent() || '',
  setContent: (content) => ueditorRef.value?.setContent(content),
  getContentTxt: () => ueditorRef.value?.getContentTxt() || '',
  getEditor: () => ueditorRef.value?.getEditor(),
  triggerCatchRemoteImage: () => ueditorRef.value?.triggerCatchRemoteImage()
})
</script>
