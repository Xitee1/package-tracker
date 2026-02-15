import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getAdminRoutes, getUserRoutes } from '@/core/moduleRegistry'

// Import module manifests to trigger registration
import '@/modules/analysers/llm'
import '@/modules/providers/email-global'
import '@/modules/providers/email-user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
      beforeEnter: async () => {
        const auth = useAuthStore()
        if (auth.setupCompleted === null) {
          await auth.checkStatus()
        }
      },
    },
    { path: '/setup', redirect: '/login' },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/orders',
      name: 'orders',
      component: () => import('@/views/OrdersView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/orders/:id',
      name: 'order-detail',
      component: () => import('@/views/OrderDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
      meta: { requiresAuth: true },
    },
    // Provider user routes (dynamically from modules)
    {
      path: '/providers',
      meta: { requiresAuth: true },
      children: getUserRoutes(),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/AboutView.vue'),
      meta: { requiresAuth: true },
    },
    // Legacy redirects
    { path: '/accounts', redirect: '/providers/email-user' },
    { path: '/accounts/imap', redirect: '/providers/email-user' },
    { path: '/accounts/forwarding', redirect: '/providers/email-global' },
    { path: '/admin/llm', redirect: '/admin/settings/llm' },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/settings',
      component: () => import('@/views/admin/SettingsView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/settings/queue' },
        {
          path: 'queue',
          name: 'queue-settings',
          component: () => import('@/views/admin/QueueSettingsView.vue'),
        },
        {
          path: 'analysers',
          name: 'analysers-settings',
          component: () => import('@/views/admin/AnalysersView.vue'),
        },
        // Module admin routes (dynamically from modules)
        ...getAdminRoutes(),
      ],
    },
    {
      path: '/admin/status',
      name: 'admin-status',
      component: () => import('@/views/admin/StatusView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    { path: '/admin/system', redirect: '/admin/status' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.isLoggedIn && !auth.user) {
    await auth.fetchUser()
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login' }
  }
  if (to.meta.guest && auth.isLoggedIn) {
    return { name: 'dashboard' }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'dashboard' }
  }
})

export default router
