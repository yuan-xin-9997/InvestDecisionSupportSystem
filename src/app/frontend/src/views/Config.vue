<template>
  <el-row :gutter="16">
    <el-col :span="12">
      <el-card shadow="never">
        <template #header>运行信息</template>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="系统名称">{{ info.app_name }}</el-descriptions-item>
          <el-descriptions-item label="系统版本">v{{ info.version }}（GitHub 提交数）</el-descriptions-item>
          <el-descriptions-item label="启动时间">{{ info.started_at }}</el-descriptions-item>
          <el-descriptions-item label="运行时长">{{ info.uptime_seconds }} 秒</el-descriptions-item>
          <el-descriptions-item label="Python">{{ info.python_version }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ info.platform }}</el-descriptions-item>
          <el-descriptions-item label="时区">{{ info.timezone }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" style="margin-top: 16px">
        <template #header>文件路径</template>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item v-for="(v, k) in paths" :key="k" :label="pathLabel(k)">
            {{ v }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </el-col>

    <el-col :span="12">
      <el-card shadow="never">
        <template #header>主配置（config/app.json，密码已脱敏）</template>
        <pre class="config-json">{{ JSON.stringify(config, null, 2) }}</pre>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const info = ref({})
const config = ref({})
const paths = ref({})

onMounted(async () => {
  try {
    info.value = await api.get('/system/info')
    const c = await api.get('/system/config')
    config.value = c.config
    paths.value = c.paths
  } catch (e) { ElMessage.error(e.message) }
})

function pathLabel(k) {
  return { base_dir: '工程目录', config_file: '配置文件', sqlite_file: 'SQLite 数据库',
           logs_dir: '日志目录', password_file: '用户密码文件' }[k] || k
}
</script>

<style scoped>
.config-json {
  background: #16274a; color: #cfe3ff; padding: 16px; border-radius: 8px;
  font-size: 12px; line-height: 1.7; max-height: 560px; overflow: auto;
}
</style>
