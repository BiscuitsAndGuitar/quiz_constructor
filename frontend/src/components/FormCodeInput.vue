<script setup>
import { ref, useId } from 'vue'
import { useRouter } from 'vue-router'
import { parseFormCode } from '../utils/participant.js'
defineProps({ label: { type: String, default: 'Ввести код' } })
const router = useRouter(), id = useId(), value = ref(''), error = ref('')
async function open() {
  const code = parseFormCode(value.value)
  error.value = code ? '' : 'Введите код'
  if (code) await router.push(`/f/${encodeURIComponent(code)}`)
}
</script>
<template>
  <form class="code-form" novalidate @submit.prevent="open">
    <label :for="id">{{ label }}</label>
    <div class="actions"><input :id="id" v-model="value" :aria-invalid="!!error" :aria-describedby="`${id}-error`"><button>Перейти</button></div>
    <p v-if="error" :id="`${id}-error`" class="error" role="alert">{{ error }}</p>
  </form>
</template>
