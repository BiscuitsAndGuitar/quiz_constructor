<script setup>
import FormCodeInput from '../components/FormCodeInput.vue'
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
</script>

<template>
  <section>
    <h1>Конструктор опросов и тестов</h1>
    <p>Создавайте опросы и тесты или проходите их по приглашению.</p>
    <p v-if="!auth.user" class="actions"><RouterLink to="/login">Войти</RouterLink><RouterLink to="/register">Зарегистрироваться</RouterLink></p>
    <p v-else><RouterLink :to="auth.homePath">{{ auth.user.is_author ? 'Мои опросы и тесты' : 'Мои прохождения' }}</RouterLink></p>
    <FormCodeInput label="Введите код опроса или теста" />
  </section>
</template>
