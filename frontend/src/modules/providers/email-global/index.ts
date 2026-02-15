import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'email-global',
  name: 'modules.email-global.title',
  type: 'provider',
  adminRoutes: [
    {
      path: 'email-global',
      component: () => import('./AdminGlobalMailView.vue'),
      label: 'modules.email-global.title',
    },
  ],
  userRoutes: [
    {
      path: 'email-global',
      component: () => import('./UserForwardingView.vue'),
      label: 'modules.email-global.userTitle',
    },
  ],
})
