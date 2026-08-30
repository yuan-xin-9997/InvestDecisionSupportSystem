<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in cards" :key="card.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ card.value ?? '...' }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>系统信息</template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="系统版本">v{{ info.version }}</el-descriptions-item>
            <el-descriptions-item label="启动时间">{{ info.started_at }}</el-descriptions-item>
            <el-descriptions-item label="运行时长">{{ uptimeText }}</el-descriptions-item>
            <el-descriptions-item label="服务器时间">{{ info.server_time }}（北京时间）</el-descriptions-item>
            <el-descriptions-item label="Python 版本">{{ info.python_version }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>行情数据库状态</template>
          <el-alert v-if="dbError" type="error" :title="dbError" :closable="false" />
          <el-descriptions v-else :column="1" border size="small">
            <el-descriptions-item label="连接状态">
              <el-tag type="success">正常</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="K 线记录数">{{ dbStatus.bar_count?.toLocaleString() }}</el-descriptions-item>
            <el-descriptions-item label="品种数">{{ barSymbols }}</el-descriptions-item>
          </el-descriptions>
          <el-button size="small" style="margin-top: 12px" @click="loadAll">刷新</el-button>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>快捷入口</template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/market')">查看行情</el-button>
        <el-button type="success" @click="$router.push('/journal')">写投资日志</el-button>
        <el-button @click="$router.push('/datasets')">维护跟踪数据</el-button>
        <el-button @click="$router.push('/tasks')">任务中心</el-button>
      </el-space>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, getStoredUser } from '../api'

const user = getStoredUser()
const info = ref({})
const cards = ref([
  { label: '行情品种数', value: null },
  { label: '投资日志数', value: null },
  { label: '跟踪数据集', value: null },
  { label: '系统版本', value: null },
])
const dbStatus = ref({})
const dbError = ref('')
const barSymbols = ref(0)

const uptimeText = computed(() => {
  const s = info.value.uptime_seconds || 0
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h} 小时 ${m} 分` : `${m} 分 ${s % 60} 秒`
})

onMounted(loadAll)

async function loadAll() {
  api.get('/system/info').then(v => {
    info.value = v
    cards.value[3].value = 'v' + v.version
  }).catch(() => {})

  api.get('/market/overview').then(v => {
    barSymbols.value = new Set(v.bars.map(b => b.symbol)).size
    cards.value[0].value = barSymbols.value
    dbError.value = ''
  }).catch(e => { dbError.value = e.message })

  api.get('/journal', { page: 1, page_size: 1 }).then(v => { cards.value[1].value = v.total }).catch(() => {})
  api.get('/datasets').then(v => { cards.value[2].value = v.total }).catch(() => {})
  api.get('/tasks/postgres_check/runs', { limit: 1 })
    .then(v => { if (v.items[0]?.status === 'success') dbStatus.value = { bar_count: parseCount(v.items[0].message) } })
    .catch(() => {})
}

function parseCount(msg) {
  const m = msg.match(/K线记录 ([\d,]+) 条/)
  return m ? Number(m[1].replace(/,/g, '')) : null
}
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-value { font-size: 26px; font-weight: 700; color: #1f2d3d; }
.stat-label { color: #909399; font-size: 13px; margin-top: 4px; }
</style>
