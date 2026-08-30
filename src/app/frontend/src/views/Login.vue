<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-title">
        <img src="/favicon.png" alt="logo" class="logo" />
        <h2>投资决策支持系统</h2>
        <p>Invest Decision Support System</p>
      </div>
      <el-form :model="form" @keyup.enter="doLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" autofocus>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="doLogin">
          登 录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { api, storeSession } from '../api'

const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function doLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await api.post('/auth/login', { username: form.username, password: form.password })
    storeSession(data.token, data.user)
    ElMessage.success(`欢迎回来，${data.user.username}`)
    router.push(route.query.redirect || '/')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #16274a 0%, #1f3f74 55%, #2b5aa0 100%);
}
.login-card {
  width: 380px;
  padding: 40px 36px 32px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
}
.login-title { text-align: center; margin-bottom: 26px; }
.login-title .logo { width: 52px; height: 52px; }
.login-title h2 { margin: 10px 0 4px; color: #1f2d3d; }
.login-title p { margin: 0; color: #909399; font-size: 12px; letter-spacing: 1px; }
</style>
