<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-head">
        <span>可登录用户与页面权限</span>
        <span>
          <el-button size="small" @click="syncFromFile">从 password.txt 同步</el-button>
          <el-button size="small" type="primary" @click="load">刷新</el-button>
        </span>
      </div>
    </template>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px"
              title="用户名单与密码维护在 src/data/password.txt（格式 username:password:role）；本页面维护角色与可见页面权限。admin 角色默认拥有全部页面。" />

    <el-table :data="users" v-loading="loading">
      <el-table-column prop="username" label="用户名" width="160" />
      <el-table-column label="角色" width="140">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">
            {{ row.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="可见页面" min-width="360">
        <template #default="{ row }">
          <el-checkbox-group v-model="row.pages" :disabled="row.role === 'admin'">
            <el-checkbox v-for="p in pageOptions" :key="p.key" :value="p.key" :label="p.key">
              {{ p.title }}
            </el-checkbox>
          </el-checkbox-group>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最近登录" width="170" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.not_synced" type="warning" size="small">未同步</el-tag>
          <el-tag v-else type="success" size="small">已同步</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="110" align="center">
        <template #default="{ row }">
          <el-button size="small" type="primary" :disabled="row.role === 'admin' && row.not_synced"
                     @click="save(row)">保存</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const users = ref([])
const loading = ref(false)
const pageOptions = [
  { key: 'dashboard', title: '系统概览' },
  { key: 'market', title: '行情展示' },
  { key: 'journal', title: '投资日志' },
  { key: 'datasets', title: '数据管理' },
  { key: 'tasks', title: '任务中心' },
]

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [u, p] = await Promise.all([api.get('/users'), api.get('/users/pages')])
    users.value = u.items
    pageOptions.value = p.pages.map(key => ({
      key,
      title: { dashboard: '系统概览', market: '行情展示', journal: '投资日志', datasets: '数据管理',
               tasks: '任务中心', users: '权限管理', config: '系统配置' }[key] || key,
    }))
  } catch (e) { ElMessage.error(e.message) }
  finally { loading.value = false }
}

async function save(row) {
  try {
    await api.put(`/users/${row.username}`, { role: row.role, pages: row.pages })
    ElMessage.success(`已保存 ${row.username} 的权限`)
    await load()
  } catch (e) { ElMessage.error(e.message) }
}

async function syncFromFile() {
  try {
    const r = await api.post('/users/sync')
    ElMessage.success(`同步完成：新增 ${r.created.length}，更新 ${r.updated.length}`)
    await load()
  } catch (e) { ElMessage.error(e.message) }
}
</script>

<style scoped>
.card-head { display: flex; justify-content: space-between; align-items: center; }
</style>
