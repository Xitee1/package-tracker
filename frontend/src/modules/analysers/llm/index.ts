import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'llm',
  name: 'modules.llm.title',
  type: 'analyser',
  adminRoutes: [
    {
      path: 'llm',
      component: () => import('./AdminLLMConfigView.vue'),
      label: 'modules.llm.title',
    },
  ],
})
