import { request } from './client.js'
import { useAuthStore } from '../stores/auth.js'

async function formsRequest(path, options = {}) {
  const auth = useAuthStore()
  try {
    return await request(path, { ...options, token: auth.token })
  } catch (error) {
    if (error.status === 401) auth.logout()
    throw error
  }
}

export const listForms = () => formsRequest('/my/forms')
export const createForm = (data) => formsRequest('/forms', { method: 'POST', body: data })
export const getForm = (id) => formsRequest(`/forms/${encodeURIComponent(id)}`)
export const saveForm = (id, data) => formsRequest(`/forms/${encodeURIComponent(id)}`, { method: 'PUT', body: data })
export const deleteForm = (id) => formsRequest(`/forms/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const publishForm = (id) => formsRequest(`/forms/${encodeURIComponent(id)}/publish`, { method: 'POST' })
export const copyForm = (id) => formsRequest(`/forms/${encodeURIComponent(id)}/copy`, { method: 'POST' })
