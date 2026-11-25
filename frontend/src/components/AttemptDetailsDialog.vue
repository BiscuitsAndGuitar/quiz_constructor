<script setup>
import { onMounted, ref } from 'vue'
defineProps({ details: { type: Object, required: true }, isTest: Boolean })
const emit = defineEmits(['close'])
const dialog = ref(null)
onMounted(() => dialog.value.showModal())
</script>

<template>
  <dialog ref="dialog" class="attempt-details-dialog" aria-labelledby="attempt-details-heading" @cancel.prevent="emit('close')">
    <h2 id="attempt-details-heading">{{ details.title }}</h2>
    <article v-for="answer in details.answers" :key="answer.question_id">
      <p class="plain-text">Блок: {{ answer.blockTitle }}</p>
      <p class="plain-text">Вопрос: {{ answer.text }}</p>
      <p>Ответ участника:</p>
      <ul v-if="answer.selected_options.length"><li v-for="option in answer.selected_options" :key="option.id" class="plain-text">{{ option.text }}</li></ul>
      <p v-else class="plain-text participant-answer">{{ answer.text_answer || 'нет ответа' }}</p>
      <p v-if="isTest">Баллы: {{ answer.score }} из {{ answer.max_points }}</p>
    </article>
    <button autofocus @click="emit('close')">Закрыть</button>
  </dialog>
</template>

<style scoped>
.attempt-details-dialog { width: min(800px, calc(100vw - 48px)); max-height: 85vh; overflow-y: auto; overflow-wrap: anywhere; }
article { border-bottom: 1px solid #ccc; padding-bottom: 1rem; margin-bottom: 1rem; }
.participant-answer { margin-left: 1.5rem; }
</style>
