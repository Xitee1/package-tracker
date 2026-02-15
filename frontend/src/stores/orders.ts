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

export interface OrderState {
  id: number
  status: string
  source_type: string | null
  source_info: string | null
  created_at: string
}

export interface OrderDetail extends Order {
  states: OrderState[]
}

export interface CreateOrderData {
  vendor_name: string
  order_number?: string | null
  tracking_number?: string | null
  carrier?: string | null
  vendor_domain?: string | null
  status?: string
  order_date?: string | null
  total_amount?: number | null
  currency?: string | null
  estimated_delivery?: string | null
  items?: OrderItem[] | null
}

export interface OrderCounts {
  total: number
  ordered: number
  shipment_preparing: number
  shipped: number
  in_transit: number
  out_for_delivery: number
  delivered: number
}

export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(25)
  const counts = ref<OrderCounts>({
    total: 0,
    ordered: 0,
    shipment_preparing: 0,
    shipped: 0,
    in_transit: 0,
    out_for_delivery: 0,
    delivered: 0,
  })

  async function fetchOrders(params?: {
    status?: string
    search?: string
    page?: number
    per_page?: number
  }) {
    loading.value = true
    try {
      const res = await api.get('/orders', { params })
      orders.value = res.data.items
      total.value = res.data.total
      page.value = res.data.page
      perPage.value = res.data.per_page
    } finally {
      loading.value = false
    }
  }

  async function fetchCounts(params?: { search?: string }) {
    const res = await api.get('/orders/counts', { params })
    counts.value = res.data
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

  async function createOrder(data: CreateOrderData): Promise<Order> {
    const res = await api.post('/orders', data)
    return res.data
  }

  return {
    orders,
    loading,
    total,
    page,
    perPage,
    counts,
    fetchOrders,
    fetchCounts,
    fetchOrder,
    updateOrder,
    deleteOrder,
    createOrder,
  }
})
