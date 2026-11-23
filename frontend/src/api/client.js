const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function request(path, { method = 'GET', body, token } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  let response
  try {
    response = await fetch(`${baseUrl}${path}`, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error('Не удалось связаться с сервером. Попробуйте ещё раз.')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(typeof data?.detail === 'string' ? data.detail : 'Не удалось выполнить запрос')
    error.status = response.status
    error.detail = data?.detail
    error.problems = data?.problems
    throw error
  }
  return data
}
