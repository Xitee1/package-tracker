import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface EmailAccount {
  id: number
  name: string
  imap_host: string
  imap_port: number
  username: string
  use_ssl: boolean
  polling_interval: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateAccountPayload {
  name: string
  imap_host: string
  imap_port: number
  username: string
  password: string
  use_ssl: boolean
  polling_interval: number
}

export interface UpdateAccountPayload {
  name?: string
  imap_host?: string
  imap_port?: number
  username?: string
  password?: string
  use_ssl?: boolean
  polling_interval?: number
  is_active?: boolean
}

export interface IMAPFolder {
  name: string
}

export interface WatchedFolder {
  id: number
  account_id: number
  folder_name: string
  created_at: string
}

export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref<EmailAccount[]>([])
  const loading = ref(false)

  async function fetchAccounts() {
    loading.value = true
    try {
      const res = await api.get('/accounts')
      accounts.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function createAccount(data: CreateAccountPayload): Promise<EmailAccount> {
    const res = await api.post('/accounts', data)
    accounts.value.push(res.data)
    return res.data
  }

  async function updateAccount(id: number, data: UpdateAccountPayload): Promise<EmailAccount> {
    const res = await api.patch(`/accounts/${id}`, data)
    const idx = accounts.value.findIndex((a) => a.id === id)
    if (idx !== -1) accounts.value[idx] = res.data
    return res.data
  }

  async function deleteAccount(id: number): Promise<void> {
    await api.delete(`/accounts/${id}`)
    accounts.value = accounts.value.filter((a) => a.id !== id)
  }

  async function testConnection(id: number): Promise<{ success: boolean; message: string }> {
    const res = await api.post(`/accounts/${id}/test`)
    return res.data
  }

  async function fetchFolders(id: number): Promise<IMAPFolder[]> {
    const res = await api.get(`/accounts/${id}/folders`)
    return res.data
  }

  async function fetchWatchedFolders(id: number): Promise<WatchedFolder[]> {
    const res = await api.get(`/accounts/${id}/folders/watched`)
    return res.data
  }

  async function addWatchedFolder(id: number, folderName: string): Promise<WatchedFolder> {
    const res = await api.post(`/accounts/${id}/folders/watched`, { folder_name: folderName })
    return res.data
  }

  async function removeWatchedFolder(id: number, folderName: string): Promise<void> {
    await api.delete(`/accounts/${id}/folders/watched`, { data: { folder_name: folderName } })
  }

  return {
    accounts,
    loading,
    fetchAccounts,
    createAccount,
    updateAccount,
    deleteAccount,
    testConnection,
    fetchFolders,
    fetchWatchedFolders,
    addWatchedFolder,
    removeWatchedFolder,
  }
})
