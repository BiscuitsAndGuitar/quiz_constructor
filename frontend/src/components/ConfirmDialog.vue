<script setup>
import { onBeforeUnmount, ref } from 'vue'

const dialog = ref(null)
const title = ref('')
const message = ref('')
const confirmText = ref('Продолжить')
const cancelText = ref('Отмена')
let pending = null
let resolveAnswer = null

function ask(options) {
  if (pending) return pending
  title.value = options.title
  message.value = options.message
  confirmText.value = options.confirmText || 'Продолжить'
  cancelText.value = options.cancelText || 'Отмена'
  pending = new Promise(resolve => { resolveAnswer = resolve })
  dialog.value.showModal()
  return pending
}

function finish(answer) {
  const resolve = resolveAnswer
  resolveAnswer = null
  pending = null
  dialog.value?.close()
  resolve?.(answer)
}

onBeforeUnmount(() => finish(false))
defineExpose({ ask })
</script>

<template>
  <dialog ref="dialog" :aria-label="title" @cancel.prevent="finish(false)">
    <h2>{{ title }}</h2>
    <p>{{ message }}</p>
    <div class="actions">
      <button type="button" autofocus @click="finish(false)">{{ cancelText }}</button>
      <button type="button" @click="finish(true)">{{ confirmText }}</button>
    </div>
  </dialog>
</template>
