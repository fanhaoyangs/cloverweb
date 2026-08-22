<template>
  <div class="bbs-node-admin">
    <div class="toolbar">
      <span class="hint">板块按「排序值」升序展示；停用后不再出现在前台，但其下话题仍可访问</span>
      <div class="spacer"></div>
      <el-button type="primary" @click="openEdit(null)">＋ 新建板块</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column label="图标" width="70" align="center">
        <template #default="{ row }">{{ row.icon || '—' }}</template>
      </el-table-column>
      <el-table-column prop="name" label="名称" width="140" />
      <el-table-column prop="slug" label="标识" width="120" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '—' }}</template>
      </el-table-column>
      <el-table-column prop="order" label="排序" width="80" align="center" />
      <el-table-column prop="topicCount" label="话题数" width="90" align="center" />
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.isActive ? 'success' : 'info'" size="small">
            {{ row.isActive ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="仅管理员发帖" width="110" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.staffOnly" @change="toggleStaffOnly(row)" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.isActive" @change="toggleActive(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑/新建对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? `编辑板块：${editing.name}` : '新建板块'" width="460px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：花园行动" maxlength="30" />
        </el-form-item>
        <el-form-item label="标识" required>
          <el-input
            v-model="form.slug"
            placeholder="英文/数字/连字符，如 garden"
            :disabled="!!editing && editing.topicCount > 0"
          />
          <div v-if="editing && editing.topicCount > 0" class="field-hint">该板块下有话题，标识暂不可改</div>
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="一个 emoji，如 🌱" maxlength="4" style="width: 120px" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="板块定位，展示于前台 tooltip" maxlength="120" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.order" :min="0" :max="999" />
          <div class="field-hint">数值小的排前面</div>
        </el-form-item>
        <el-form-item label="管理员发帖">
          <el-switch v-model="form.staffOnly" />
          <div class="field-hint">开启后普通用户只能浏览/回复，不能在该板块发帖</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminListNodes, adminCreateNode, adminUpdateNode, adminDeleteNode } from '@/api/bbs'

const loading = ref(false)
const list = ref([])
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = reactive({ name: '', slug: '', icon: '', description: '', order: 0, staffOnly: false })

onMounted(load)

async function load() {
  loading.value = true
  try {
    list.value = await adminListNodes()
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  editing.value = row
  Object.assign(form, row
    ? { name: row.name, slug: row.slug, icon: row.icon, description: row.description, order: row.order, staffOnly: row.staffOnly }
    : { name: '', slug: '', icon: '', description: '', order: (list.value.length + 1) * 10, staffOnly: false })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('名称不能为空')
    return
  }
  if (!/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(form.slug)) {
    ElMessage.warning('标识只能用小写英文、数字和连字符，且不以连字符开头/结尾')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await adminUpdateNode(editing.value.slug, {
        name: form.name.trim(),
        icon: form.icon,
        description: form.description,
        order: form.order,
        staffOnly: form.staffOnly
      })
      ElMessage.success('已保存')
    } else {
      await adminCreateNode({
        name: form.name.trim(),
        slug: form.slug,
        icon: form.icon,
        description: form.description,
        order: form.order,
        staffOnly: form.staffOnly,
        isActive: true
      })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    const detail = e?.response?.data?.slug?.[0] || e?.response?.data?.detail
    ElMessage.error(detail ? `保存失败：${detail}` : '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

async function toggleActive(row) {
  try {
    const updated = await adminUpdateNode(row.slug, { isActive: !row.isActive })
    Object.assign(row, updated)
    ElMessage.success(updated.isActive ? '已启用' : '已停用（前台不再展示）')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function toggleStaffOnly(row) {
  try {
    const updated = await adminUpdateNode(row.slug, { staffOnly: !row.staffOnly })
    Object.assign(row, updated)
  } catch {
    ElMessage.error('操作失败')
  }
}

function remove(row) {
  ElMessageBox.confirm(`确定删除板块「${row.name}」？`, '删除确认', { type: 'warning' })
    .then(async () => {
      try {
        await adminDeleteNode(row.slug)
        ElMessage.success('已删除')
        load()
      } catch (e) {
        ElMessage.error(e?.response?.data?.detail || '删除失败')
      }
    })
    .catch(() => {})
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.hint {
  font-size: 12px;
  color: #8a9a8b;
}

.spacer {
  flex: 1;
}

.field-hint {
  font-size: 12px;
  color: #8a9a8b;
  line-height: 1.4;
  margin-top: 2px;
}
</style>
