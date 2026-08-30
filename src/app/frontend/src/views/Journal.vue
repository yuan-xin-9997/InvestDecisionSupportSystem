<template>
  <div>
    <el-card shadow="never">
      <el-form inline>
        <el-form-item label="日期范围">
          <el-date-picker v-model="filters.range" type="daterange" value-format="YYYY-MM-DD"
                          start-placeholder="开始" end-placeholder="结束" style="width: 250px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="搜索日志内容" clearable style="width: 200px"
                    @keyup.enter="load(1)" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load(1)">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" @click="openCreate">写日志</el-button>
        </el-form-item>
      </el-form>

      <el-empty v-if="!items.length && !loading" description="暂无日志，点击右上角「写日志」开始记录" />

      <el-timeline v-else style="padding-left: 6px">
        <el-timeline-item v-for="j in items" :key="j.id" :timestamp="j.trade_date"
                          placement="top" type="primary">
          <el-card shadow="hover" class="journal-card">
            <div class="journal-head">
              <span class="journal-time">{{ j.created_at }}</span>
              <span>
                <el-button text size="small" @click="openEdit(j)">编辑</el-button>
                <el-button text size="small" type="danger" @click="remove(j)">删除</el-button>
              </span>
            </div>
            <div class="journal-content">{{ j.content }}</div>
            <div v-if="j.images.length" class="journal-images">
              <el-image v-for="img in j.images" :key="img.id" :src="img.url"
                        :preview-src-list="j.images.map(i => i.url)" :initial-index="j.images.indexOf(img)"
                        fit="cover" class="thumb" preview-teleported hide-on-click-modal loading="lazy" />
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>

      <div style="display: flex; justify-content: center; margin-top: 14px">
        <el-pagination background layout="prev, pager, next, total" :total="total"
                       :page-size="pageSize" :current-page="page" @current-change="load" />
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑日志' : '写投资日志'" width="640px" top="6vh">
      <el-form label-width="80px">
        <el-form-item label="日期">
          <el-date-picker v-model="dialog.trade_date" type="date" value-format="YYYY-MM-DD"
                          placeholder="默认为今天" />
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="dialog.content" type="textarea" :rows="8"
                    placeholder="记录今日行情观察、操作思路、仓位变化……" />
        </el-form-item>
        <el-form-item v-if="!dialog.isEdit" label="图片">
          <el-input type="hidden" />
          <label class="upload-box">
            <input type="file" accept="image/*" multiple hidden @change="onPickFiles" />
            <el-icon size="26"><Plus /></el-icon>
            <div>点击选择图片（可多选）</div>
          </label>
          <div class="preview-list" v-if="dialog.files.length">
            <div v-for="(f, i) in dialog.files" :key="i" class="preview-item">
              <img :src="f.url" />
              <el-icon class="remove" @click="dialog.files.splice(i, 1)"><CircleCloseFilled /></el-icon>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, CircleCloseFilled } from '@element-plus/icons-vue'
import { api } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const filters = reactive({ range: null, keyword: '' })

const dialog = reactive({
  visible: false, isEdit: false, id: null,
  content: '', trade_date: '', files: [], saving: false,
})

onMounted(() => load(1))

async function load(p) {
  if (p) page.value = p
  loading.value = true
  try {
    const data = await api.get('/journal', {
      start_date: filters.range?.[0], end_date: filters.range?.[1],
      keyword: filters.keyword, page: page.value, page_size: pageSize,
    })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.range = null
  filters.keyword = ''
  load(1)
}

function openCreate() {
  Object.assign(dialog, { visible: true, isEdit: false, id: null, content: '', trade_date: '', files: [] })
}

function openEdit(j) {
  Object.assign(dialog, { visible: true, isEdit: true, id: j.id, content: j.content, trade_date: j.trade_date, files: [] })
}

function onPickFiles(e) {
  for (const f of e.target.files) {
    dialog.files.push({ file: f, url: URL.createObjectURL(f) })
  }
  e.target.value = ''
}

async function save() {
  dialog.saving = true
  try {
    if (dialog.isEdit) {
      await api.put(`/journal/${dialog.id}`, { content: dialog.content, trade_date: dialog.trade_date })
      ElMessage.success('已保存')
    } else {
      const fd = new FormData()
      fd.append('content', dialog.content)
      if (dialog.trade_date) fd.append('trade_date', dialog.trade_date)
      for (const f of dialog.files) fd.append('files', f.file)
      await api.upload('/journal', fd)
      ElMessage.success('日志已发布')
    }
    dialog.visible = false
    load(1)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    dialog.saving = false
  }
}

async function remove(j) {
  await ElMessageBox.confirm(`确定删除 ${j.trade_date} 的这条日志吗？图片将一并删除。`, '删除确认', { type: 'warning' })
  try {
    await api.delete(`/journal/${j.id}`)
    ElMessage.success('已删除')
    load(page.value)
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.journal-card { max-width: 860px; }
.journal-head { display: flex; justify-content: space-between; color: #909399; font-size: 12px; }
.journal-content { margin-top: 8px; white-space: pre-wrap; line-height: 1.7; color: #303133; }
.journal-images { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.thumb { width: 96px; height: 96px; border-radius: 6px; border: 1px solid #e8ebf1; }
.upload-box {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  width: 140px; height: 90px; border: 1px dashed #c0c8d8; border-radius: 8px;
  color: #909399; cursor: pointer; font-size: 12px; gap: 4px;
}
.upload-box:hover { border-color: #2b5aa0; color: #2b5aa0; }
.preview-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.preview-item { position: relative; width: 84px; height: 84px; }
.preview-item img { width: 100%; height: 100%; object-fit: cover; border-radius: 6px; }
.preview-item .remove {
  position: absolute; top: -6px; right: -6px; color: #f56c6c;
  background: #fff; border-radius: 50%; font-size: 18px; cursor: pointer;
}
</style>
