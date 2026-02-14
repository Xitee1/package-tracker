import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
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
    {
      path: '/setup',
      redirect: '/login',
    },
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
    {
      path: '/accounts',
      name: 'accounts',
      component: () => import('@/views/AccountsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/llm',
      redirect: '/admin/settings/llm',
    },
    {
      path: '/admin/settings',
      component: () => import('@/views/admin/SettingsView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          redirect: '/admin/settings/llm',
        },
        {
          path: 'llm',
          name: 'settings-llm',
          component: () => import('@/views/admin/LLMConfigView.vue'),
        },
        {
          path: 'imap',
          name: 'settings-imap',
          component: () => import('@/views/admin/ImapSettingsView.vue'),
        },
        {
          path: 'queue',
          name: 'queue-settings',
          component: () => import('@/views/admin/QueueSettingsView.vue'),
        },
        {
          path: 'modules',
          name: 'settings-modules',
          component: () => import('@/views/admin/ModulesView.vue'),
        },
        {
          path: 'email',
          name: 'settings-email',
          component: () => import('@/views/admin/GlobalMailConfigView.vue'),
        },
      ],
    },
    {
      path: '/admin/system',
      name: 'admin-system',
      component: () => import('@/views/admin/SystemView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
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
