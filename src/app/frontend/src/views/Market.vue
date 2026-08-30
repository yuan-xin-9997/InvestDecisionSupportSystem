<template>
  <div>
    <el-card shadow="never">
      <el-form inline>
        <el-form-item label="品种">
          <el-select v-model="sel.symbol" filterable style="width: 260px" placeholder="选择品种">
            <el-option v-for="o in symbolOptions" :key="o.key" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="sel.interval" style="width: 100px">
            <el-option label="日线" value="d" />
            <el-option label="1小时" value="1h" />
            <el-option label="1分钟" value="1m" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
                          start-placeholder="开始" end-placeholder="结束" style="width: 260px" />
        </el-form-item>
        <el-form-item label="根数">
          <el-input-number v-model="sel.limit" :min="50" :max="5000" :step="100" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadKline">查询</el-button>
          <el-radio-group v-model="viewMode" style="margin-left: 12px">
            <el-radio-button value="chart">K 线图</el-radio-button>
            <el-radio-button value="table">表格</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-alert v-if="error" type="error" :title="error" :closable="false" style="margin-bottom: 12px" />

      <div v-show="viewMode === 'chart'" ref="chartEl" class="chart"></div>

      <el-table v-if="viewMode === 'table'" :data="bars" size="small" stripe height="560"
                :default-sort="{ prop: 'datetime', order: 'descending' }">
        <el-table-column prop="datetime" label="时间" width="170" sortable />
        <el-table-column prop="open" label="开盘" align="right" />
        <el-table-column prop="high" label="最高" align="right" />
        <el-table-column prop="low" label="最低" align="right" />
        <el-table-column prop="close" label="收盘" align="right" />
        <el-table-column prop="volume" label="成交量" align="right" />
        <el-table-column prop="turnover" label="成交额" align="right" />
        <el-table-column prop="open_interest" label="持仓量" align="right" />
      </el-table>

      <div v-if="bars.length" class="summary">
        共 {{ bars.length }} 根 K 线
        <template v-if="bars.length">
          ｜最新收盘 <b :class="lastChange >= 0 ? 'up' : 'down'">{{ lastClose }}</b>
          （{{ lastChange >= 0 ? '+' : '' }}{{ (lastChange * 100).toFixed(2) }}%）
        </template>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const sel = reactive({ symbol: '', interval: 'd', limit: 500 })
const dateRange = ref(null)
const viewMode = ref('chart')
const loading = ref(false)
const error = ref('')
const bars = ref([])
const overview = ref({ bars: [], ticks: [] })
const chartEl = ref(null)
let chart = null

const INTERVAL_LABEL = { d: '日线', '1h': '1小时', '1m': '1分钟' }

const symbolOptions = computed(() => {
  const seen = new Map()
  for (const b of overview.value.bars) {
    const key = `${b.symbol}|${b.exchange}`
    if (!seen.has(key)) seen.set(key, { symbol: b.symbol, exchange: b.exchange, intervals: [] })
    seen.get(key).intervals.push(b.interval)
  }
  return [...seen.values()].map(v => ({
    key: `${v.symbol}|${v.exchange}`,
    value: `${v.symbol}|${v.exchange}`,
    label: `${v.symbol}（${v.exchange}）`,
    intervals: v.intervals,
  }))
})

const lastClose = computed(() => bars.value.length ? bars.value[bars.value.length - 1].close : null)
const lastChange = computed(() => {
  if (bars.value.length < 2) return 0
  const prev = bars.value[bars.value.length - 2].close
  return prev ? (lastClose.value - prev) / prev : 0
})

onMounted(async () => {
  window.addEventListener('resize', resizeChart)
  try {
    overview.value = await api.get('/market/overview')
  } catch (e) {
    error.value = e.message
  }
  // 默认选中第一个有日线的品种
  const first = symbolOptions.value.find(s => s.intervals.includes('d')) || symbolOptions.value[0]
  if (first) sel.symbol = first.value
  if (sel.symbol) await loadKline()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
})

function resizeChart() { chart?.resize() }

watch(viewMode, (v) => { if (v === 'chart') setTimeout(resizeChart, 50) })

watch(sel.symbol, (val) => {
  const opt = symbolOptions.value.find(s => s.value === val)
  if (opt && opt.intervals.length && !opt.intervals.includes(sel.interval)) {
    sel.interval = opt.intervals.includes('d') ? 'd' : opt.intervals[0]
  }
})

async function loadKline() {
  if (!sel.symbol) return
  const [symbol, exchange] = sel.symbol.split('|')
  loading.value = true
  error.value = ''
  try {
    const data = await api.get('/market/kline', {
      symbol, exchange, interval: sel.interval,
      start: dateRange.value?.[0], end: dateRange.value?.[1], limit: sel.limit,
    })
    bars.value = data.bars
    if (!data.bars.length) ElMessage.warning('该区间没有数据，请调整筛选条件')
    if (viewMode.value === 'chart') renderChart(symbol, exchange)
  } catch (e) {
    error.value = e.message
    bars.value = []
  } finally {
    loading.value = false
  }
}

function ma(n) {
  const closes = bars.value.map(b => b.close)
  return closes.map((_, i) => {
    if (i < n - 1) return null
    let s = 0
    for (let k = i - n + 1; k <= i; k++) s += closes[k]
    return +(s / n).toFixed(3)
  })
}

function renderChart(symbol, exchange) {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const dateLen = sel.interval === 'd' ? 10 : 16
  const dates = bars.value.map(b => b.datetime.slice(0, dateLen))
  const kdata = bars.value.map(b => [b.open, b.close, b.low, b.high])
  const vols = bars.value.map((b, i) => ({
    value: b.volume,
    itemStyle: { color: b.close >= b.open ? '#eb4d3d' : '#2eb872' },
  }))

  chart.setOption({
    animation: false,
    backgroundColor: '#fff',
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255,255,255,0.96)',
    },
    legend: { data: ['MA5', 'MA10', 'MA20'], top: 4 },
    grid: [
      { left: 70, right: 24, top: 34, height: '56%' },
      { left: 70, right: 24, top: '74%', height: '16%' },
    ],
    xAxis: [
      { type: 'category', data: dates, boundaryGap: true, axisLine: { lineStyle: { color: '#c0c4cc' } } },
      { type: 'category', gridIndex: 1, data: dates, axisLabel: { show: false } },
    ],
    yAxis: [
      { scale: true, splitLine: { lineStyle: { color: '#eef0f4' } } },
      { gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 55, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], top: '93%', height: 18, start: 55, end: 100 },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', data: kdata,
        itemStyle: { color: '#eb4d3d', color0: '#2eb872', borderColor: '#eb4d3d', borderColor0: '#2eb872' },
        markPoint: undefined,
      },
      { name: 'MA5', type: 'line', data: ma(5), showSymbol: false, lineStyle: { width: 1 } },
      { name: 'MA10', type: 'line', data: ma(10), showSymbol: false, lineStyle: { width: 1 } },
      { name: 'MA20', type: 'line', data: ma(20), showSymbol: false, lineStyle: { width: 1 } },
      { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: vols },
    ],
  }, true)
  chart.resize()
}
</script>

<style scoped>
.chart { width: 100%; height: 560px; }
.summary { margin-top: 10px; color: #606266; font-size: 13px; }
.up { color: #d83931; }
.down { color: #1e9e5a; }
</style>
