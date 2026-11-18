import { request } from './client.js'

export const register = (data) => request('/auth/register', { method: 'POST', body: data })
export const login = (data) => request('/auth/login', { method: 'POST', body: data })
export const getMe = (token) => request('/auth/me', { token })
