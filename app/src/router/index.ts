/**
 * Vue Router configuration for TinyBase Admin UI
 *
 * Defines routes for all admin pages and handles authentication guards.
 * Also includes public auth portal routes.
 */

import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

// Lazy-loaded route components
const Login = () => import('../views/Login.vue');
const Dashboard = () => import('../views/Dashboard.vue');
const Collections = () => import('../views/Collections.vue');
const CollectionDetail = () => import('../views/CollectionDetail.vue');
const Users = () => import('../views/Users.vue');
const Functions = () => import('../views/Functions.vue');
const Schedules = () => import('../views/Schedules.vue');
const FunctionCalls = () => import('../views/FunctionCalls.vue');
const Settings = () => import('../views/Settings.vue');
const Extensions = () => import('../views/Extensions.vue');
const Files = () => import('../views/Files.vue');

// Auth portal views
const AuthLogin = () => import('../views/auth/AuthLogin.vue');
const AuthRegister = () => import('../views/auth/AuthRegister.vue');
const AuthPasswordResetRequest = () => import('../views/auth/AuthPasswordResetRequest.vue');
const AuthPasswordResetConfirm = () => import('../views/auth/AuthPasswordResetConfirm.vue');

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    // Admin login (for admin UI)
    {
      path: '/admin/login',
      name: 'admin-login',
      component: Login,
      meta: { requiresAuth: false },
    },
    // Auth portal routes (public)
    {
      path: '/auth/login',
      name: 'auth-login',
      component: AuthLogin,
      meta: { requiresAuth: false, isAuthPortal: true },
    },
    {
      path: '/auth/register',
      name: 'auth-register',
      component: AuthRegister,
      meta: { requiresAuth: false, isAuthPortal: true },
    },
    {
      path: '/auth/password-reset',
      name: 'auth-password-reset-request',
      component: AuthPasswordResetRequest,
      meta: { requiresAuth: false, isAuthPortal: true },
    },
    {
      path: '/auth/password-reset/:token',
      name: 'auth-password-reset-confirm',
      component: AuthPasswordResetConfirm,
      meta: { requiresAuth: false, isAuthPortal: true },
    },
    {
      path: '/admin',
      name: 'dashboard',
      component: Dashboard,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/collections',
      name: 'collections',
      component: Collections,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/collections/:name',
      name: 'collection-detail',
      component: CollectionDetail,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'users',
      component: Users,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/functions',
      name: 'functions',
      component: Functions,
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/schedules',
      name: 'schedules',
      component: Schedules,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/function-calls',
      name: 'function-calls',
      component: FunctionCalls,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/settings',
      name: 'settings',
      component: Settings,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/extensions',
      name: 'extensions',
      component: Extensions,
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/files',
      name: 'files',
      component: Files,
      meta: { requiresAuth: true },
    },
    // Root redirect to admin dashboard
    {
      path: '/',
      redirect: '/admin',
    },
    // Auth root redirect to login
    {
      path: '/auth',
      redirect: '/auth/login',
    },
    // Catch-all - redirect to admin login (not dashboard, to avoid auth loops)
    {
      path: '/:pathMatch(.*)*',
      redirect: '/admin/login',
    },
  ],
});

// Navigation guard for authentication
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  // Try to load user from stored token
  if (!authStore.user && authStore.accessToken) {
    try {
      await authStore.fetchUser();
    } catch {
      authStore.logout();
    }
  }

  const requiresAuth = to.meta.requiresAuth !== false;
  const requiresAdmin = to.meta.requiresAdmin === true;

  // Auth portal routes don't require authentication
  const isAuthPortal = to.meta.isAuthPortal === true;

  if (requiresAuth && !authStore.isAuthenticated && !isAuthPortal) {
    // Redirect to admin login if not authenticated (not for auth portal)
    // Only add redirect query if we're not already going to login
    if (to.name !== 'admin-login') {
      next({ name: 'admin-login', query: { redirect: to.fullPath } });
    } else {
      next();
    }
  } else if (requiresAdmin && !authStore.isAdmin) {
    // Redirect to dashboard if not admin
    next({ name: 'dashboard' });
  } else if (to.name === 'admin-login' && authStore.isAuthenticated) {
    // Redirect to dashboard if already logged in (admin login)
    next({ name: 'dashboard' });
  } else {
    next();
  }
});

export default router;
