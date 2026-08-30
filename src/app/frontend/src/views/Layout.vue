<template>
  <el-container class="layout" v-if="user">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <img src="/favicon.png" alt="logo" />
        <div>
          <div class="brand-name">投资决策支持系统</div>
          <div class="brand-sub">InvestDSS</div>
        </div>
      </div>

      <el-menu :default-active="activeMenu" router class="menu" background-color="#16274a"
               text-color="#aebbd6" active-text-color="#ffffff">
        <el-menu-item v-for="item in allowedMenus" :key="item.key" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>

      <!-- 左下角：当前用户 + 退出 + 版本号 -->
      <div class="user-corner">
        <div class="user-row">
          <el-avatar :size="34" class="avatar">{{ user.username.slice(0, 1).toUpperCase() }}</el-avatar>
          <div class="user-meta">
            <div class="username">{{ user.username }}</div>
            <div class="role">{{ user.role === 'admin' ? '管理员' : '普通用户' }}</div>
          </div>
          <el-button text size="small" class="logout-btn" @click="doLogout">
            <el-icon><SwitchButton /></el-icon>&nbsp;退出
          </el-button>
        </div>
        <div class="version">版本 v{{ version }}</div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">{{ today }}</div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Odometer, TrendCharts, Notebook, Coin, Timer, UserFilled, Setting, SwitchButton,
} from '@element-plus/icons-vue'
import { api, clearSession, getStoredUser } from '../api'

const route = useRoute()
const router = useRouter()
const user = ref(getStoredUser())
const version = ref('...')

const MENUS = [
  { key: 'dashboard', path: '/', title: '系统概览', icon: Odometer },
  { key: 'market', path: '/market', title: '行情展示', icon: TrendCharts },
  { key: 'journal', path: '/journal', title: '投资日志', icon: Notebook },
  { key: 'datasets', path: '/datasets', title: '数据管理', icon: Coin },
  { key: 'tasks', path: '/tasks', title: '任务中心', icon: Timer },
  { key: 'users', path: '/users', title: '权限管理', icon: UserFilled, adminOnly: true },
  { key: 'config', path: '/config', title: '系统配置', icon: Setting, adminOnly: true },
]

const allowedMenus = computed(() =>
  MENUS.filter(m => {
    if (user.value.role === 'admin') return true
    if (m.adminOnly) return false
    return (user.value.pages || []).includes(m.key)
  })
)

const activeMenu = computed(() => route.path)
const currentTitle = computed(() =>
  MENUS.find(m => m.path === route.path)?.title || '投资决策支持系统')
const today = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

onMounted(async () => {
  try {
    const info = await api.get('/system/info')
    version.value = info.version
    localStorage.setItem('idss_version', info.version)
  } catch { /* 忽略，显示占位 */ }
})

async function doLogout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  try { await api.post('/auth/logout') } catch { /* 忽略 */ }
  clearSession()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }
.layout { height: 100vh; }
.aside {
  display: flex;
  flex-direction: column;
  background: #16274a;
}
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 16px 14px;
}
.brand img { width: 36px; height: 36px; }
.brand-name { color: #fff; font-size: 15px; font-weight: 600; white-space: nowrap; }
.brand-sub { color: #7c8db0; font-size: 11px; letter-spacing: 1.5px; }
.menu { border-right: none; flex: 1; }
.menu .el-menu-item.is-active { background: #2b5aa0 !important; }
.menu .el-menu-item:hover { background: #1f3f74; }

.user-corner {
  padding: 12px 14px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.user-row { display: flex; align-items: center; gap: 10px; }
.avatar { background: #2b5aa0; color: #fff; font-weight: 600; }
.user-meta { flex: 1; min-width: 0; }
.username { color: #fff; font-size: 13px; line-height: 1.3; }
.role { color: #7c8db0; font-size: 11px; }
.logout-btn { color: #aebbd6; }
.logout-btn:hover { color: #fff; }
.version {
  margin-top: 10px;
  color: #5d6f94;
  font-size: 11px;
  text-align: center;
  letter-spacing: 0.5px;
}

.header {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e8ebf1;
  height: 56px;
}
.header-title { font-size: 17px; font-weight: 600; color: #1f2d3d; }
.header-right { color: #909399; font-size: 13px; }
.main { background: #f4f6fa; padding: 18px; overflow: auto; }
</style>
