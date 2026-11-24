<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { previewForm } from '../utils/participant.js'
import AttemptFlow from './AttemptFlow.vue'
const props = defineProps({ form: { type: Object, required: true } })
const emit = defineEmits(['close'])
const form = previewForm(props.form)
const state = ref({ form, answers: {}, pageKey: null, position: 0 })
const dialog = ref(null), flow = ref(null), ended = ref(false), message = ref(''), run = ref(0)
let closed = false
let previousOverflow
onMounted(() => {
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  dialog.value.showModal()
})
onBeforeUnmount(() => {
  closed = true
  document.body.style.overflow = previousOverflow
  dialog.value?.close()
})
async function finish() {
  const result = await flow.value.prepareFinish()
  if (!result || closed) return
  message.value = result.rule?.message || form.completion_message || 'Спасибо за участие!'
  ended.value = true
}
function restart() {
  state.value = { form, answers: {}, pageKey: null, position: 0 }
  run.value++
  ended.value = false
}
</script>
<template>
  <Teleport to="body">
    <dialog ref="dialog" class="preview-dialog" aria-label="Предпросмотр формы" @cancel.prevent="emit('close')">
      <div class="preview-toolbar"><strong>Предпросмотр: ответы не сохраняются</strong><button type="button" @click="emit('close')">Закрыть предпросмотр</button></div>
      <div class="preview-content">
        <template v-if="ended">
          <h1>Конец предпросмотра</h1><p v-if="!form.is_test" class="plain-text">{{ message }}</p>
          <div class="actions"><button type="button" @click="restart">Пройти заново</button><button type="button" @click="emit('close')">Закрыть предпросмотр</button></div>
        </template>
        <template v-else><h1>{{ form.title }}</h1><AttemptFlow :key="run" ref="flow" :state="state" @finish="finish" /></template>
      </div>
    </dialog>
  </Teleport>
</template>
