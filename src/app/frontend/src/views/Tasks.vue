<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <span>任务列表</span>
          <el-button size="small" @click="load">刷新</el-button>
        </div>
      </template>
      <el-table :data="tasks" v-loading="loading">
        <el-table-column prop="task_id" label="任务ID" width="200" />
        <el-table-column prop="name" label="任务名称" width="180" />
        <el-table-column prop="description" label="说明" min-width="220" />
        <el-table-column label="最近运行" min-width="240">
          <template #default="{ row }">
            <template v-if="row.last_run">
              <div>
                <el-tag size="small" :type="row.last_run.status === 'success' ? 'success' : row.last_run.status === 'failed' ? 'danger' : 'info'">
                  {{ statusText(row.last_run.status) }}
                </el-tag>
                {{ row.last_run.started_at }}
              </div>
              <div class="run-msg">{{ row.last_run.message }}</div>
            </template>
            <span v-else style="color: #c0c4cc">从未运行</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" :loading="running === row.task_id" @click="run(row)">
              立即运行
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="drawer.visible" :title="`运行历史 - ${drawer.task?.name || ''}`" size="55%">
      <el-timeline style="padding-left: 4px">
        <el-timeline-item v-for="r in drawer.runs" :key="r.id" :timestamp="r.started_at"
                          :type="r.status === 'success' ? 'success' : r.status === 'failed' ? 'danger' : 'primary'">
          <el-tag size="small" :type="r.status === 'success' ? 'success' : r.status === 'failed' ? 'danger' : 'info'">
            {{ statusText(r.status) }}
          </el-tag>
          <span style="margin-left: 8px; color: #909399; font-size: 12px">
            结束于 {{ r.finished_at || '-' }}
          </span>
          <div class="log-box">{{ r.message }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="!drawer.runs.length" description="暂无运行记录" />
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const tasks = ref([])
const loading = ref(false)
const running = ref('')
const drawer = reactive({ visible: false, task: null, runs: [] })

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await api.get('/tasks')
    tasks.value = data.items
  } catch (e) { ElMessage.error(e.message) }
  finally { loading.value = false }
}

async function run(task) {
  running.value = task.task_id
  try {
    const data = await api.post(`/tasks/${task.task_id}/run`)
    if (data.run.status === 'success') {
      ElMessage.success(`任务成功：${data.run.message}`)
    } else {
      ElMessage.error(`任务失败：${data.run.message}`)
    }
    await load()
  } catch (e) { ElMessage.error(e.message) }
  finally { running.value = '' }
}

async function openHistory(task) {
  drawer.task = task
  drawer.visible = true
  try {
    const data = await api.get(`/tasks/${task.task_id}/runs`, { limit: 30 })
    drawer.runs = data.items
  } catch (e) { ElMessage.error(e.message) }
}

function statusText(s) {
  return { success: '成功', failed: '失败', running: '运行中' }[s] || s
}
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.run-msg { color: #909399; font-size: 12px; margin-top: 4px; }
.log-box {
  margin-top: 8px; padding: 10px; background: #f5f7fa; border-radius: 6px;
  font-size: 13px; color: #303133; white-space: pre-wrap;
}
</style>
