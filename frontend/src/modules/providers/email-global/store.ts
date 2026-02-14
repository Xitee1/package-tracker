import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface SenderAddress {
  id: number
  email_address: string
  created_at: string
}

export const useSenderAddressesStore = defineStore('senderAddresses', () => {
  const addresses = ref<SenderAddress[]>([])
  const loading = ref(false)

  async function fetchAddresses() {
    loading.value = true
    try {
      const res = await api.get('/providers/email-global/sender-addresses')
      addresses.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function addAddress(email: string): Promise<SenderAddress> {
    const res = await api.post('/providers/email-global/sender-addresses', { email_address: email })
    addresses.value.push(res.data)
    return res.data
  }

  async function removeAddress(id: number) {
    await api.delete(`/providers/email-global/sender-addresses/${id}`)
    addresses.value = addresses.value.filter((a) => a.id !== id)
  }

  return { addresses, loading, fetchAddresses, addAddress, removeAddress }
})
