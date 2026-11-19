<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createForm, deleteForm, listForms } from '../api/forms.js'
import NoAccessPage from './NoAccessPage.vue'

const route = useRoute()
const router = useRouter()
const forms = ref([])
const loading = ref(true)
const loadError = ref('')
const forbidden = ref(false)
const typeFilter = ref('all')
const statusFilter = ref('all')
const createDialog = ref(null)
const deleteDialog = ref(null)
const newTitle = ref('')
const newIsTest = ref(false)
const creating = ref(false)
const createError = ref('')
const deleting = ref(false)
const deleteError = ref('')
const selectedForm = ref(null)

const visibleForms = computed(() => forms.value.filter(form =>
  (typeFilter.value === 'all' || form.is_test === (typeFilter.value === 'test')) &&
  (statusFilter.value === 'all' || form.is_published === (statusFilter.value === 'published')),
))

function returnToLogin(error) {
  if (error.status === 401) router.replace({ path: '/login', query: { redirect: route.fullPath } })
}

async function loadForms() {
  loading.value = true
  loadError.value = ''
  forbidden.value = false
  try {
    forms.value = await listForms()
  } catch (error) {
    forbidden.value = error.status === 403
    loadError.value = error.message
    returnToLogin(error)
  } finally {
    loading.value = false
  }
}

function openCreate(isTest) {
  newTitle.value = ''
  newIsTest.value = isTest
  createError.value = ''
  createDialog.value.showModal()
}

function closeCreate() {
  if (!creating.value) createDialog.value.close()
}

async function submitCreate() {
  if (creating.value) return
  const title = newTitle.value.trim()
  if ([...title].length < 1 || [...title].length > 255) {
    createError.value = 'Название должно содержать от 1 до 255 символов'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const form = await createForm({ title, is_test: newIsTest.value })
    createDialog.value.close()
    await router.push(`/forms/${form.id}/edit`)
  } catch (error) {
    createError.value = error.message
    returnToLogin(error)
  } finally {
    creating.value = false
  }
}

function openDelete(form) {
  selectedForm.value = form
  deleteError.value = ''
  deleteDialog.value.showModal()
}

function closeDelete() {
  if (!deleting.value) deleteDialog.value.close()
}

async function confirmDelete() {
  if (deleting.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteForm(selectedForm.value.id)
    forms.value = forms.value.filter(form => form.id !== selectedForm.value.id)
    deleteDialog.value.close()
  } catch (error) {
    deleteError.value = error.message
    returnToLogin(error)
  } finally {
    deleting.value = false
  }
}

function formatDate(value) {
  // timestamp в API хранится в UTC, даже если строка приходит без суффикса Z.
  const utc = /Z$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`
  return new Date(utc).toLocaleString('ru-RU')
}

onMounted(loadForms)
</script>

<template>
  <NoAccessPage v-if="forbidden" />
  <section v-else>
    <h1>Мои опросы и тесты</h1>
    <div class="actions">
      <button @click="openCreate(false)">Создать опрос</button>
      <button @click="openCreate(true)">Создать тест</button>
    </div>
    <div class="filters">
      <label>Тип <select v-model="typeFilter"><option value="all">Все типы</option><option value="survey">Опросы</option><option value="test">Тесты</option></select></label>
      <label>Статус <select v-model="statusFilter"><option value="all">Все статусы</option><option value="draft">Черновики</option><option value="published">Опубликованные</option></select></label>
    </div>
    <p v-if="loading" role="status">Загрузка…</p>
    <div v-else-if="loadError" role="alert" class="error"><p>{{ loadError }}</p><button @click="loadForms">Повторить</button></div>
    <p v-else-if="!visibleForms.length">{{ forms.length ? 'Нет форм с выбранными фильтрами.' : 'У вас пока нет опросов и тестов.' }}</p>
    <div v-else class="table-scroll">
      <table>
        <thead><tr><th>Название</th><th>Тип</th><th>Статус</th><th>Доступ</th><th>Число прохождений</th><th>Дата создания</th><th>Действия</th></tr></thead>
        <tbody>
          <tr v-for="form in visibleForms" :key="form.id">
            <td>{{ form.title }}</td><td>{{ form.is_test ? 'Тест' : 'Опрос' }}</td>
            <td>{{ form.is_published ? 'Опубликован' : 'Черновик' }}</td><td>{{ form.requires_login ? 'Авторизованным' : 'Всем' }}</td>
            <td>{{ form.attempts_count }}</td><td>{{ formatDate(form.created_at) }}</td>
            <td><div class="actions"><RouterLink v-if="!form.is_published" :to="`/forms/${form.id}/edit`">Редактировать</RouterLink><button @click="openDelete(form)">Удалить</button></div></td>
          </tr>
        </tbody>
      </table>
    </div>
    <dialog ref="createDialog" aria-labelledby="create-heading" @cancel.prevent="closeCreate">
      <h2 id="create-heading">{{ newIsTest ? 'Создать тест' : 'Создать опрос' }}</h2>
      <form novalidate @submit.prevent="submitCreate">
        <div class="field"><label for="new-title">Название</label><input id="new-title" v-model="newTitle" autofocus :disabled="creating" aria-describedby="create-error"></div>
        <p v-if="createError" id="create-error" class="error" role="alert">{{ createError }}</p>
        <div class="actions"><button :disabled="creating">{{ creating ? 'Создаём…' : 'Создать' }}</button><button type="button" :disabled="creating" @click="closeCreate">Отмена</button></div>
      </form>
    </dialog>
    <dialog ref="deleteDialog" aria-labelledby="delete-heading" @cancel.prevent="closeDelete">
      <h2 id="delete-heading">Удалить форму?</h2>
      <p>{{ selectedForm?.title }}</p><p>Будут удалены форма и все прохождения</p>
      <p v-if="deleteError" class="error" role="alert">{{ deleteError }}</p>
      <div class="actions"><button :disabled="deleting" @click="confirmDelete">{{ deleting ? 'Удаляем…' : 'Удалить' }}</button><button autofocus :disabled="deleting" @click="closeDelete">Отмена</button></div>
    </dialog>
  </section>
</template>
