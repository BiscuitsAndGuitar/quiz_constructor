<script setup>
import { ref } from 'vue'
import { request, baseUrl } from '../api/client.js'
import { useAuthStore } from '../stores/auth.js'
import { imageFileError, imageUploadError, imageUrl } from '../utils/images.js'
const props = defineProps({ modelValue: Object, readOnly: Boolean })
const emit = defineEmits(['update:modelValue'])
const loading = ref(false), error = ref(''), input = ref(null)
async function upload(event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file || loading.value || props.readOnly) return
  error.value = imageFileError(file)
  if (error.value) return
  loading.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    const image = await request('/images', { method: 'POST', body, token: useAuthStore().token })
    if (!props.readOnly) emit('update:modelValue', image)
  } catch (err) { error.value = imageUploadError(err) }
  finally { loading.value = false }
}
</script>

<template>
  <div class="field">
    <img v-if="modelValue" :src="imageUrl(modelValue.url, baseUrl)" class="question-image" alt="Иллюстрация к вопросу">
    <div v-if="!readOnly" class="actions">
      <input ref="input" hidden type="file" accept="image/jpeg,image/png,image/webp,image/gif" :disabled="loading" @change="upload">
      <button type="button" :disabled="loading" @click="input.click()">{{ loading ? 'Загрузка…' : 'Добавить картинку' }}</button>
      <button v-if="modelValue" type="button" :disabled="loading" @click="emit('update:modelValue', null)">Убрать</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>
