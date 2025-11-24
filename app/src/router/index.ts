/**
 * Vue Router configuration for TinyBase Admin UI
 * 
 * Defines routes for all admin pages and handles authentication guards.
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Lazy-loaded route components
const Login = () => import('../views/Login.vue')
const Dashboard = () => import('../views/Dashboard.vue')
const Collections = () => import('../views/Collections.vue')
const CollectionDetail = () => import('../views/CollectionDetail.vue')
const Users = () => import('../views/Users.vue')
const Functions = () => import('../views/Functions.vue')
const Schedules = () => import('../views/Schedules.vue')
const FunctionCalls = () => import('../views/FunctionCalls.vue')

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard,
      meta: { requiresAuth: true },
    },
    {
      path: '/collections',
      name: 'collections',
      component: Collections,
      meta: { requiresAuth: true },
    },
    {
      path: '/collections/:name',
      name: 'collection-detail',
      component: CollectionDetail,
      meta: { requiresAuth: true },
    },
    {
      path: '/users',
      name: 'users',
      component: Users,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/functions',
      name: 'functions',
      component: Functions,
      meta: { requiresAuth: true },
    },
    {
      path: '/schedules',
      name: 'schedules',
      component: Schedules,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/function-calls',
      name: 'function-calls',
      component: FunctionCalls,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    // Catch-all redirect to dashboard
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// Navigation guard for authentication
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  
  // Try to load user from stored token
  if (!authStore.user && authStore.token) {
    try {
      await authStore.fetchUser()
    } catch {
      authStore.logout()
    }
  }
  
  const requiresAuth = to.meta.requiresAuth !== false
  const requiresAdmin = to.meta.requiresAdmin === true
  
  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login if not authenticated
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (requiresAdmin && !authStore.isAdmin) {
    // Redirect to dashboard if not admin
    next({ name: 'dashboard' })
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    // Redirect to dashboard if already logged in
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router

