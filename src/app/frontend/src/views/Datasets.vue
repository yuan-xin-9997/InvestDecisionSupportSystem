<template>
  <el-row :gutter="16">
    <!-- 左侧：数据集列表 -->
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>
          <div class="card-head">
            <span>跟踪数据集</span>
            <el-button size="small" type="primary" @click="openCreate">新建</el-button>
          </div>
        </template>
        <el-radio-group v-model="catFilter" size="small" style="margin-bottom: 10px" @change="loadDatasets">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button v-for="c in categories" :key="c" :value="c">{{ c }}</el-radio-button>
        </el-radio-group>
        <el-menu :default-active="String(selectedId)" @select="id => selectDataset(Number(id))" class="ds-menu">
          <el-menu-item v-for="d in datasets" :key="d.id" :index="String(d.id)">
            <div class="ds-item">
              <div>
                <div class="ds-name">{{ d.name }}</div>
                <div class="ds-meta">{{ d.category }}<template v-if="d.unit"> · {{ d.unit }}</template></div>
              </div>
              <el-tag size="small" type="info">{{ d.record_count }}</el-tag>
            </div>
          </el-menu-item>
        </el-menu>
        <el-empty v-if="!datasets.length" description="暂无数据集" :image-size="70" />
      </el-card>
    </el-col>

    <!-- 右侧：记录管理 -->
    <el-col :span="16">
      <el-card shadow="never" v-if="!current">
        <el-empty description="选择左侧数据集查看记录" />
      </el-card>

      <template v-else>
        <el-card shadow="never" style="margin-bottom: 14px">
          <template #header>
            <div class="card-head">
              <span>{{ current.name }}
                <el-tag size="small" style="margin-left: 8px">{{ current.category }}</el-tag>
                <span class="ds-desc" v-if="current.description">{{ current.description }}</span>
              </span>
              <span>
                <el-button size="small" @click="importVisible = true">导入 CSV</el-button>
                <el-button size="small" @click="exportCsv">导出 CSV</el-button>
                <el-button size="small" type="warning" @click="removeDataset">删除数据集</el-button>
              </span>
            </div>
          </template>

          <div ref="lineChartEl" class="line-chart"></div>

          <el-form inline style="margin-top: 12px">
            <el-form-item label="日期"><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 140px" /></el-form-item>
            <el-form-item label="数值"><el-input-number v-model="form.value" :precision="4" :controls="false" style="width: 120px" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="form.note" style="width: 180px" /></el-form-item>
            <el-form-item><el-button type="primary" @click="saveRecord">保存记录</el-button></el-form-item>
          </el-form>

          <el-table :data="records" size="small" stripe>
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="value" label="数值" align="right" width="130" />
            <el-table-column prop="note" label="备注" show-overflow-tooltip />
            <el-table-column prop="updated_at" label="更新时间" width="170" />
            <el-table-column label="操作" width="130" align="center">
              <template #default="{ row }">
                <el-button text size="small" @click="editRecord(row)">编辑</el-button>
                <el-button text size="small" type="danger" @click="removeRecord(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination background layout="prev, pager, next, total" :total="recordTotal"
                         :page-size="recordPageSize" :current-page="recordPage"
                         @current-change="loadRecords" style="margin-top: 10px; justify-content: center" />
        </el-card>
      </template>
    </el-col>

    <!-- 新建数据集 -->
    <el-dialog v-model="createVisible" title="新建数据集" width="460px">
      <el-form label-width="70px">
        <el-form-item label="名称"><el-input v-model="createForm.name" placeholder="如：CPI 同比" /></el-form-item>
        <el-form-item label="分类">
          <el-radio-group v-model="createForm.category">
            <el-radio v-for="c in categories" :key="c" :value="c">{{ c }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="单位"><el-input v-model="createForm.unit" placeholder="如：% / 亿元 / 点" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="createForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="createDataset">创建</el-button>
      </template>
    </el-dialog>

    <!-- CSV 导入 -->
    <el-dialog v-model="importVisible" title="导入 CSV" width="460px">
      <el-alert type="info" :closable="false" title="CSV 格式：表头 date,value,note（UTF-8 或 GBK 编码），同日期数据将覆盖更新"
                style="margin-bottom: 12px" />
      <input type="file" accept=".csv" @change="onPickCsv" />
      <div v-if="importResult" style="margin-top: 10px">
        <el-result :icon="importResult.skipped ? 'warning' : 'success'"
                   :title="`新增 ${importResult.inserted}，更新 ${importResult.updated}，跳过 ${importResult.skipped}`" />
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </el-row>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { api, getStoredUser } from '../api'

const categories = ['宏观', '微观', '其他']
const catFilter = ref('')
const datasets = ref([])
const selectedId = ref(null)
const current = ref(null)
const records = ref([])
const recordTotal = ref(0)
const recordPage = ref(1)
const recordPageSize = 20

const createVisible = ref(false)
const createForm = reactive({ name: '', category: '宏观', unit: '', description: '' })
const importVisible = ref(false)
const importResult = ref(null)
const form = reactive({ date: '', value: undefined, note: '' })
const lineChartEl = ref(null)
let lineChart = null
const user = getStoredUser()

onMounted(loadDatasets)

async function loadDatasets() {
  try {
    const data = await api.get('/datasets', { category: catFilter.value || undefined })
    datasets.value = data.items
    if (selectedId.value && !data.items.some(d => d.id === selectedId.value)) {
      selectedId.value = null
      current.value = null
    }
  } catch (e) { ElMessage.error(e.message) }
}

async function selectDataset(id) {
  selectedId.value = id
  current.value = datasets.value.find(d => d.id === id)
  recordPage.value = 1
  await loadRecords(1)
}

async function loadRecords(p) {
  if (p) recordPage.value = p
  try {
    const data = await api.get(`/datasets/${selectedId.value}/records`, {
      page: recordPage.value, page_size: recordPageSize,
    })
    records.value = data.items
    recordTotal.value = data.total
    await nextTick()
    renderChart()
  } catch (e) { ElMessage.error(e.message) }
}

function renderChart() {
  if (!lineChartEl.value) return
  if (!lineChart) lineChart = echarts.init(lineChartEl.value)
  const asc = [...records.value].reverse()
  lineChart.setOption({
    animation: false,
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 24, top: 20, bottom: 46 },
    xAxis: { type: 'category', data: asc.map(r => r.date) },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }],
    series: [{
      type: 'line', data: asc.map(r => r.value), showSymbol: true,
      lineStyle: { color: '#2b5aa0', width: 2 }, itemStyle: { color: '#2b5aa0' },
    }],
  }, true)
  lineChart.resize()
}

function openCreate() {
  Object.assign(createForm, { name: '', category: '宏观', unit: '', description: '' })
  createVisible.value = true
}

async function createDataset() {
  try {
    await api.post('/datasets', { ...createForm })
    ElMessage.success('数据集已创建')
    createVisible.value = false
    await loadDatasets()
  } catch (e) { ElMessage.error(e.message) }
}

async function saveRecord() {
  if (!form.date) { ElMessage.warning('请选择日期'); return }
  try {
    await api.post(`/datasets/${selectedId.value}/records`, {
      date: form.date, value: form.value ?? null, note: form.note,
    })
    ElMessage.success('已保存')
    form.date = ''; form.value = undefined; form.note = ''
    await loadRecords(1)
    await loadDatasets()
  } catch (e) { ElMessage.error(e.message) }
}

function editRecord(row) {
  Object.assign(form, { date: row.date, value: row.value, note: row.note })
}

async function removeRecord(row) {
  await ElMessageBox.confirm(`删除 ${row.date} 的记录？`, '提示', { type: 'warning' })
  try {
    await api.delete(`/datasets/records/${row.id}`)
    loadRecords(recordPage.value)
    loadDatasets()
  } catch (e) { ElMessage.error(e.message) }
}

async function removeDataset() {
  await ElMessageBox.confirm(
    `删除数据集「${current.value.name}」及其全部 ${current.value.record_count} 条记录？`, '删除确认',
    { type: 'error' })
  try {
    await api.delete(`/datasets/${selectedId.value}`)
    selectedId.value = null
    current.value = null
    loadDatasets()
    ElMessage.success('已删除')
  } catch (e) { ElMessage.error(e.message) }
}

async function exportCsv() {
  try {
    const resp = await fetch(`/api/datasets/${selectedId.value}/export`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('idss_token')}` },
    })
    if (!resp.ok) throw new Error('导出失败')
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${current.value.name}.csv`
    a.click()
  } catch (e) { ElMessage.error(e.message) }
}

async function onPickCsv(e) {
  const file = e.target.files[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    importResult.value = await api.upload(`/datasets/${selectedId.value}/import`, fd)
    loadRecords(1)
    loadDatasets()
  } catch (err) {
    ElMessage.error(err.message)
  } finally {
    e.target.value = ''
  }
}
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
.ds-menu { border-right: none; }
.ds-item { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.ds-name { font-size: 14px; color: #303133; }
.ds-meta { font-size: 12px; color: #909399; }
.ds-desc { color: #909399; font-size: 12px; margin-left: 10px; font-weight: 400; }
.line-chart { width: 100%; height: 240px; }
</style>
