import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'email-global',
  name: 'Email - Global/Redirect',
  type: 'provider',
  adminRoutes: [
    {
      path: 'email-global',
      component: () => import('./AdminGlobalMailView.vue'),
      label: 'Email - Global/Redirect',
    },
  ],
  userRoutes: [
    {
      path: 'email-global',
      component: () => import('./UserForwardingView.vue'),
      label: 'Email Redirect',
    },
  ],
})
