import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'notify-email',
  name: 'modules.notify-email.title',
  type: 'notifier',
  adminRoutes: [
    {
      path: 'notify-email',
      component: () => import('./AdminNotifyEmailView.vue'),
      label: 'modules.notify-email.title',
    },
  ],
  userRoutes: [
    {
      path: 'notify-email',
      component: () => import('./UserNotifyEmailView.vue'),
      label: 'modules.notify-email.userTitle',
    },
  ],
})
