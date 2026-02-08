import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api/client'

export interface OrderItem {
  name: string
  quantity: number
  price: number | null
}

export interface Order {
  id: number
  order_number: string | null
  tracking_number: string | null
  carrier: string | null
  vendor_name: string | null
  vendor_domain: string | null
  status: string
  order_date: string | null
  total_amount: number | null
  currency: string | null
  items: OrderItem[] | null
  estimated_delivery: string | null
  created_at: string
  updated_at: string
}

export interface OrderEvent {
  id: number
  order_id: number
  event_type: string
  description: string | null
  timestamp: string
  raw_data: Record<string, unknown> | null
}

export interface OrderDetail extends Order {
  events: OrderEvent[]
}

export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)

  async function fetchOrders(params?: { status?: string; search?: string }) {
    loading.value = true
    try {
      const res = await api.get('/orders', { params })
      orders.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function fetchOrder(id: number): Promise<OrderDetail> {
    const res = await api.get(`/orders/${id}`)
    return res.data
  }

  async function updateOrder(id: number, data: Partial<Order>): Promise<Order> {
    const res = await api.patch(`/orders/${id}`, data)
    return res.data
  }

  async function deleteOrder(id: number): Promise<void> {
    await api.delete(`/orders/${id}`)
  }

  return { orders, loading, fetchOrders, fetchOrder, updateOrder, deleteOrder }
})
