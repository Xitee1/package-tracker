import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'email-user',
  name: 'modules.email-user.title',
  type: 'provider',
  adminRoutes: [
    {
      path: 'email-user',
      component: () => import('./AdminImapSettingsView.vue'),
      label: 'modules.email-user.title',
    },
  ],
  userRoutes: [
    {
      path: 'email-user',
      component: () => import('./UserImapAccountsView.vue'),
      label: 'modules.email-user.userTitle',
    },
  ],
})
