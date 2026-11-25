import { request } from './client.js'
import { useAuthStore } from '../stores/auth.js'

function statisticsRequest(path) {
  return request(path, { token: useAuthStore().token })
}
export const getStatistics = id => statisticsRequest(`/forms/${encodeURIComponent(id)}/stats`)
export const getFormAttempts = id => statisticsRequest(`/forms/${encodeURIComponent(id)}/attempts`)
export const getAttemptDetails = id => statisticsRequest(`/attempts/${encodeURIComponent(id)}/details`)
// Этот вспомогательный запрос не должен разлогинивать пользователя при ошибке.
export const getStatisticsForm = id => statisticsRequest(`/forms/${encodeURIComponent(id)}`)
