import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '../api/auth.js'

const storageKey = 'quiz_access_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref('')
  const initialized = ref(false)
  const initializationError = ref('')
  const homePath = computed(() => user.value?.is_author ? '/my/forms' : '/my/attempts')
  let initialization = null

  function saveToken(value) {
    token.value = value
    try {
      if (value) localStorage.setItem(storageKey, value)
      else localStorage.removeItem(storageKey)
    } catch {
      // Если хранилище недоступно, вход действует до закрытия или обновления страницы.
    }
  }

  function logout() {
    saveToken('')
    user.value = null
    initializationError.value = ''
  }

  async function login(data) {
    const result = await authApi.login(data)
    saveToken(result.access_token)
    user.value = result.user
    initializationError.value = ''
    initialized.value = true
  }

  async function register(data) {
    await authApi.register(data)
    try {
      await login({ email: data.email, password: data.password })
    } catch {
      // Регистрация уже состоялась: повторно отправлять её не нужно.
      throw new Error('Аккаунт создан, но войти автоматически не удалось. Перейдите на страницу входа.')
    }
  }

  async function loadUser() {
    initializationError.value = ''
    if (!token.value) return
    try {
      user.value = await authApi.getMe(token.value)
    } catch (error) {
      if (error.status === 401) logout()
      else initializationError.value = error.message
    }
  }

  async function initialize() {
    if (initialized.value) return
    if (initialization) return initialization
    try {
      token.value = localStorage.getItem(storageKey) || ''
    } catch {
      token.value = ''
    }
    initialization = loadUser().finally(() => {
      initialized.value = true
      initialization = null
    })
    return initialization
  }

  return { user, token, initialized, initializationError, homePath, login, register, logout, initialize, loadUser }
})
