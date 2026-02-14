import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'llm',
  name: 'LLM Config',
  type: 'analyser',
  adminRoutes: [
    {
      path: 'llm',
      component: () => import('./AdminLLMConfigView.vue'),
      label: 'LLM Config',
    },
  ],
})
