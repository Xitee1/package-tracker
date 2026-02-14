import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export interface QueueItem {
  id: number
  user_id: number
  status: string
  source_type: string
  source_info: string
  raw_data: Record<string, unknown>
  extracted_data: Record<string, unknown> | null
  error_message: string | null
  order_id: number | null
  cloned_from_id: number | null
  created_at: string
  updated_at: string
}

export interface QueueItemList {
  items: QueueItem[]
  total: number
  page: number
  per_page: number
}

export interface QueueStats {
  queued: number
  processing: number
  completed: number
  failed: number
}

export const useQueueStore = defineStore('queue', () => {
  const items = ref<QueueItemList>({ items: [], total: 0, page: 1, per_page: 50 })
  const loading = ref(false)

  async function fetchItems(params?: {
    page?: number
    per_page?: number
    status?: string
    source_type?: string
  }) {
    loading.value = true
    try {
      const { data } = await api.get<QueueItemList>('/queue', { params })
      items.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchItem(id: number): Promise<QueueItem> {
    const { data } = await api.get<QueueItem>(`/queue/${id}`)
    return data
  }

  async function deleteItem(id: number) {
    await api.delete(`/queue/${id}`)
  }

  async function retryItem(id: number): Promise<QueueItem> {
    const { data } = await api.post<QueueItem>(`/queue/${id}/retry`)
    return data
  }

  async function fetchStats(): Promise<QueueStats> {
    const { data } = await api.get<QueueStats>('/queue/stats')
    return data
  }

  return { items, loading, fetchItems, fetchItem, deleteItem, retryItem, fetchStats }
})
