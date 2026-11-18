<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const code = ref('')
const router = useRouter()
function openForm() {
  if (code.value.trim()) router.push(`/f/${encodeURIComponent(code.value.trim())}`)
}
</script>

<template>
  <section>
    <h1>Конструктор опросов и тестов</h1>
    <p>Создавайте опросы и тесты или проходите их по приглашению.</p>
    <p class="actions"><RouterLink to="/login">Войти</RouterLink><RouterLink to="/register">Зарегистрироваться</RouterLink></p>
    <form class="code-form" @submit.prevent="openForm">
      <label for="code">Введите код опроса или теста</label>
      <div class="actions"><input id="code" v-model="code" required><button>Перейти</button></div>
    </form>
  </section>
</template>
