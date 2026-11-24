import { request } from './client.js'
import { loadAttemptKey } from '../utils/attemptStorage.js'

function keyHeaders(id) {
  let key = ''
  try { key = loadAttemptKey(localStorage, id) } catch { /* Хранилище может быть запрещено браузером. */ }
  return key ? { 'X-Attempt-Key': key } : {}
}
export const getPublicForm = (code, token) => request(`/public/forms/${encodeURIComponent(code)}`, { token })
export const startAttempt = (id, token) => request(`/forms/${id}/attempts`, { method: 'POST', token })
export const finishAttempt = (id, answers, token) => request(`/attempts/${id}/finish`, {
  method: 'POST', body: { answers }, token, headers: keyHeaders(id),
})
export const getAttemptResult = (id, token) => request(`/attempts/${id}/result`, { token, headers: keyHeaders(id) })
export const getMyAttempts = token => request('/my/attempts', { token })
