import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface EmailScan {
  id: number
  account_id: number
  account_name: string | null
  folder_path: string
  email_uid: number
  message_id: string
  subject: string
  sender: string
  email_date: string | null
  is_relevant: boolean
  llm_raw_response: Record<string, unknown> | null
  order_id: number | null
  rescan_queued: boolean
  created_at: string
}

export interface EmailScanList {
  items: EmailScan[]
  total: number
  page: number
  per_page: number
}

export interface EmailContent {
  subject: string
  sender: string
  date: string | null
  body_text: string
}

export const useScanHistoryStore = defineStore('scanHistory', () => {
  const scans = ref<EmailScanList>({ items: [], total: 0, page: 1, per_page: 50 })
  const loading = ref(false)

  async function fetchScans(params?: {
    page?: number
    per_page?: number
    is_relevant?: boolean
    account_id?: number
  }) {
    loading.value = true
    try {
      const res = await api.get('/scan-history', { params })
      scans.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchScan(id: number): Promise<EmailScan> {
    const res = await api.get(`/scan-history/${id}`)
    return res.data
  }

  async function fetchEmailContent(id: number): Promise<EmailContent> {
    const res = await api.get(`/scan-history/${id}/email`)
    return res.data
  }

  async function deleteScan(id: number): Promise<void> {
    await api.delete(`/scan-history/${id}`)
  }

  async function queueRescan(id: number): Promise<EmailScan> {
    const res = await api.post(`/scan-history/${id}/rescan`)
    return res.data
  }

  return { scans, loading, fetchScans, fetchScan, fetchEmailContent, deleteScan, queueRescan }
})
