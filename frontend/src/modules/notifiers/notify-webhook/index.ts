import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'notify-webhook',
  name: 'modules.notify-webhook.title',
  type: 'notifier',
  adminRoutes: [
    {
      path: 'notify-webhook',
      component: () => import('./AdminNotifyWebhookView.vue'),
      label: 'modules.notify-webhook.title',
    },
  ],
  userRoutes: [
    {
      path: 'notify-webhook',
      component: () => import('./UserNotifyWebhookView.vue'),
      label: 'modules.notify-webhook.userTitle',
    },
  ],
})
