<script setup>
import { ref } from 'vue'
import { messageLines } from '../utils/editorDisplay.js'

const dialog = ref(null)
const title = ref('Сообщение')
const lines = ref([])

function show(message, heading = 'Не удалось выполнить действие') {
  title.value = heading
  lines.value = messageLines(message)
  if (!dialog.value.open) dialog.value.showModal()
}
function close() { dialog.value.close() }
function backdropClick(event) {
  if (event.target !== dialog.value) return
  const rect = dialog.value.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close()
}
defineExpose({ show })
</script>

<template>
  <dialog ref="dialog" class="message-dialog" :aria-label="title" @cancel.prevent="close" @click="backdropClick">
    <div class="message-heading"><h2>{{ title }}</h2><button type="button" aria-label="Закрыть сообщение" @click="close">×</button></div>
    <ul v-if="lines.length > 1"><li v-for="(line, index) in lines" :key="index">{{ line }}</li></ul>
    <p v-else>{{ lines[0] }}</p>
    <button type="button" autofocus @click="close">Понятно</button>
  </dialog>
</template>
