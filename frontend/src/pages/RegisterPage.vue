<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { passwordError } from '../utils/password.js'
import { safeRedirect } from '../utils/attempt.js'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ name: '', email: '', password: '', repeatPassword: '', is_author: null })
const errors = ref({})
const submitting = ref(false)
const generalError = ref('')

async function submit() {
  if (submitting.value) return
  errors.value = {}
  generalError.value = ''
  const name = form.name.trim()
  const email = form.email.trim().toLowerCase()
  if ([...name].length < 1 || [...name].length > 100) errors.value.name = 'Имя должно содержать от 1 до 100 символов'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.value.email = 'Укажите корректный email'
  const error = passwordError(form.password)
  if (error) errors.value.password = error
  if (form.password !== form.repeatPassword) errors.value.repeatPassword = 'Пароли не совпадают'
  if (form.is_author === null) errors.value.is_author = 'Выберите роль: составитель или участник'
  if (Object.keys(errors.value).length) return
  submitting.value = true
  try {
    await auth.register({ name, email, password: form.password, is_author: form.is_author })
    await router.replace(safeRedirect(route.query.redirect) || auth.homePath)
  } catch (error) {
    if (error.status === 409 || (error.status === 422 && error.message.includes('email'))) errors.value.email = error.message
    else if (error.status === 422 && error.message.startsWith('Пароль')) errors.value.password = error.message
    else if (error.status === 422 && error.message.startsWith('Имя')) errors.value.name = error.message
    else generalError.value = error.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <h1>Регистрация</h1>
    <form novalidate @submit.prevent="submit">
      <div class="field">
        <label for="name">Имя</label>
        <input id="name" v-model="form.name" autocomplete="name" :aria-invalid="!!errors.name" aria-describedby="name-error">
        <p v-if="errors.name" id="name-error" class="error" role="alert">{{ errors.name }}</p>
      </div>
      <div class="field">
        <label for="email">Email</label>
        <input id="email" v-model="form.email" type="email" autocomplete="email" :aria-invalid="!!errors.email" aria-describedby="email-error">
        <p v-if="errors.email" id="email-error" class="error" role="alert">{{ errors.email }}</p>
      </div>
      <div class="field">
        <label for="password">Пароль</label>
        <input id="password" v-model="form.password" type="password" autocomplete="new-password" :aria-invalid="!!errors.password" aria-describedby="password-hint password-error">
        <p id="password-hint" class="hint">Не менее 8 символов</p>
        <p v-if="errors.password" id="password-error" class="error" role="alert">{{ errors.password }}</p>
      </div>
      <div class="field">
        <label for="repeat-password">Повтор пароля</label>
        <input id="repeat-password" v-model="form.repeatPassword" type="password" autocomplete="new-password" :aria-invalid="!!errors.repeatPassword" aria-describedby="repeat-error">
        <p v-if="errors.repeatPassword" id="repeat-error" class="error" role="alert">{{ errors.repeatPassword }}</p>
      </div>
      <fieldset>
        <legend>Выберите роль</legend>
        <div class="role-cards">
          <label class="role-card">
            <input v-model="form.is_author" type="radio" name="role" :value="true">
            <span>Я составитель <small>Создаю опросы и тесты</small></span>
          </label>
          <label class="role-card">
            <input v-model="form.is_author" type="radio" name="role" :value="false">
            <span>Я участник <small>Прохожу опросы и тесты</small></span>
          </label>
        </div>
        <p class="hint">Роль нельзя изменить</p>
        <p v-if="errors.is_author" class="error" role="alert">{{ errors.is_author }}</p>
      </fieldset>
      <p v-if="generalError" class="error" role="alert">{{ generalError }}</p>
      <button :disabled="submitting">{{ submitting ? 'Регистрируем…' : 'Зарегистрироваться' }}</button>
    </form>
    <p>Уже есть аккаунт? <RouterLink :to="{ path: '/login', query: { redirect: safeRedirect(route.query.redirect) || undefined } }">Войти</RouterLink></p>
  </section>
</template>
