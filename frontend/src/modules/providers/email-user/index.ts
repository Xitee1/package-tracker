import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'email-user',
  name: 'Email - User IMAP',
  type: 'provider',
  adminRoutes: [
    {
      path: 'email-user',
      component: () => import('./AdminImapSettingsView.vue'),
      label: 'Email - User IMAP',
    },
  ],
  userRoutes: [
    {
      path: 'email-user',
      component: () => import('./UserImapAccountsView.vue'),
      label: 'Email IMAP',
    },
  ],
})
