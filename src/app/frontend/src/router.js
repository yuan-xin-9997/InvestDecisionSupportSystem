import { createRouter, createWebHashHistory } from 'vue-router'
import { getToken, getStoredUser, clearSession } from './api'

const routes = [
  { path: '/login', name: 'login', component: () => import('./views/Login.vue'), meta: { public: true } },
  { path: '/', name: 'dashboard', component: () => import('./views/Dashboard.vue'), meta: { page: 'dashboard' } },
  { path: '/market', name: 'market', component: () => import('./views/Market.vue'), meta: { page: 'market' } },
  { path: '/journal', name: 'journal', component: () => import('./views/Journal.vue'), meta: { page: 'journal' } },
  { path: '/datasets', name: 'datasets', component: () => import('./views/Datasets.vue'), meta: { page: 'datasets' } },
  { path: '/tasks', name: 'tasks', component: () => import('./views/Tasks.vue'), meta: { page: 'tasks' } },
  { path: '/users', name: 'users', component: () => import('./views/Users.vue'), meta: { page: 'users', adminOnly: true } },
  { path: '/config', name: 'config', component: () => import('./views/Config.vue'), meta: { page: 'config', adminOnly: true } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) {
    return true
  }
  const token = getToken()
  const user = getStoredUser()
  if (!token || !user) {
    clearSession()
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  const page = to.meta.page
  if (page && user.role !== 'admin' && !(user.pages || []).includes(page)) {
    return { path: '/' }
  }
  return true
})

export default router
