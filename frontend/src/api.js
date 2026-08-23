const API_URL = import.meta.env.VITE_API_URL || ''
let accessToken = localStorage.getItem('voice-cart-token') || ''

export function setAccessToken(token) {
  accessToken = token || ''
  if (accessToken) localStorage.setItem('voice-cart-token', accessToken)
  else localStorage.removeItem('voice-cart-token')
}

export function hasAccessToken() {
  return Boolean(accessToken)
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Something went wrong. Please try again.')
  }
  return response.status === 204 ? null : response.json()
}

export const api = {
  register: (credentials) => request('/api/auth/register', { method: 'POST', body: JSON.stringify(credentials) }),
  login: (credentials) => request('/api/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  me: () => request('/api/auth/me'),
  items: () => request('/api/items'),
  suggestions: () => request('/api/suggestions'),
  orders: () => request('/api/orders'),
  placeOrder: () => request('/api/orders', { method: 'POST' }),
  updateOrder: (id, status) => request(`/api/orders/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  command: (transcript, language) => request('/api/command', { method: 'POST', body: JSON.stringify({ transcript, language }) }),
  addItem: (item) => request('/api/items', { method: 'POST', body: JSON.stringify(item) }),
  updateItem: (id, item) => request(`/api/items/${id}`, { method: 'PATCH', body: JSON.stringify(item) }),
  deleteItem: (id) => request(`/api/items/${id}`, { method: 'DELETE' }),
  clear: () => request('/api/items', { method: 'DELETE' }),
}
