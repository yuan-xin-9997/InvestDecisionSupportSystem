<template>
  <el-config-provider :locale="zhCn">
    <router-view v-if="isLoginRoute" />
    <Layout v-else />
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import Layout from './views/Layout.vue'

const route = useRoute()
const isLoginRoute = computed(() => route.path === '/login')
</script>
