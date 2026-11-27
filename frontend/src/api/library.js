import { request } from './client.js'
import { useAuthStore } from '../stores/auth.js'

async function libraryRequest(path, options = {}) {
  const auth = useAuthStore()
  try { return await request(path, { ...options, token: auth.token }) }
  catch (error) {
    if (error.status === 401) auth.logout()
    throw error
  }
}
export const listLibraryBlocks = params => libraryRequest(`/library/blocks?${new URLSearchParams(params)}`)
export const getLibraryBlock = id => libraryRequest(`/library/blocks/${encodeURIComponent(id)}`)
export const createLibraryBlock = body => libraryRequest('/library/blocks', { method: 'POST', body })
export const updateLibraryBlock = (id, body) => libraryRequest(`/library/blocks/${encodeURIComponent(id)}`, { method: 'PUT', body })
export const deleteLibraryBlock = id => libraryRequest(`/library/blocks/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const libraryTags = query => libraryRequest(`/library/tags?${new URLSearchParams({ query })}`)
