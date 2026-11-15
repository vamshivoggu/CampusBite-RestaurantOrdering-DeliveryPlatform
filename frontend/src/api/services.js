import api, { cleanParams } from './client';

const data = (p) => p.then((r) => r.data);

export const authApi = {
  login: (email, password) => data(api.post('/auth/login', { email, password })),
  register: (payload) => data(api.post('/auth/register', payload)),
  me: () => data(api.get('/auth/me')),
};

export const metaApi = { get: () => data(api.get('/meta')) };

export const restaurantApi = {
  list: (params) => data(api.get('/restaurants', { params: cleanParams(params) })),
  cuisines: () => data(api.get('/restaurants/cuisines')),
  get: (id) => data(api.get(`/restaurants/${id}`)),
  menu: (id, params) => data(api.get(`/restaurants/${id}/menu`, { params: cleanParams(params) })),
  categories: (id) => data(api.get(`/restaurants/${id}/categories`)),
  reviews: (id, params) => data(api.get(`/restaurants/${id}/reviews`, { params })),
  searchDishes: (params) => data(api.get('/dishes', { params: cleanParams(params) })),
};

export const orderApi = {
  place: (payload) => data(api.post('/orders', payload)),
  mine: (params) => data(api.get('/orders', { params: cleanParams(params) })),
  get: (id) => data(api.get(`/orders/${id}`)),
  cancel: (id) => data(api.post(`/orders/${id}/cancel`)),
  review: (id, payload) => data(api.post(`/orders/${id}/review`, payload)),
  requestReturn: (id, reason) => data(api.post(`/orders/${id}/return`, { reason })),
};

export const ownerApi = {
  restaurant: () => data(api.get('/owner/restaurant')),
  updateRestaurant: (payload) => data(api.patch('/owner/restaurant', payload)),
  menu: (params) => data(api.get('/owner/menu', { params: cleanParams(params) })),
  addDish: (payload) => data(api.post('/owner/menu', payload)),
  updateDish: (id, payload) => data(api.put(`/owner/menu/${id}`, payload)),
  setAvailability: (id, isAvailable) => data(api.patch(`/owner/menu/${id}/availability`, { is_available: isAvailable })),
  deleteDish: (id) => api.delete(`/owner/menu/${id}`),
  orders: (params) => data(api.get('/owner/orders', { params: cleanParams(params) })),
  updateStatus: (id, status, note) => data(api.patch(`/owner/orders/${id}/status`, { status, note })),
  partners: () => data(api.get('/owner/delivery-partners')),
  assign: (id, partnerId) => data(api.post(`/owner/orders/${id}/assign`, { delivery_partner_id: partnerId })),
  returns: (params) => data(api.get('/owner/returns', { params: cleanParams(params) })),
  decideReturn: (id, decision, note) => data(api.post(`/owner/returns/${id}/decision`, { decision, note })),
  stats: () => data(api.get('/owner/stats')),
  reminders: (params) => data(api.get('/owner/reminders', { params })),
  scanReminders: () => data(api.post('/owner/reminders/scan')),
  resolveReminder: (id) => data(api.post(`/owner/reminders/${id}/resolve`)),
};

export const deliveryApi = {
  orders: (params) => data(api.get('/delivery/orders', { params: cleanParams(params) })),
  stats: () => data(api.get('/delivery/stats')),
  updateStatus: (id, status) => data(api.patch(`/delivery/orders/${id}/status`, { status })),
};

export const aiApi = {
  stats: () => data(api.get('/ai/stats')),
  insights: (mode, question) => data(api.post('/ai/insights', { mode, question })),
};
