<script setup>
import { RouterView, useRoute, useRouter } from 'vue-router'
import AppHeader from './components/AppHeader.vue'
import NoAccessPage from './pages/NoAccessPage.vue'
import { useAuthStore } from './stores/auth.js'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
async function retry() {
  await auth.loadUser()
  if (auth.user) router.replace(auth.homePath)
}
</script>

<template>
  <AppHeader />
  <main>
    <div v-if="auth.initializationError" role="alert" class="error">
      <p>{{ auth.initializationError }}</p><button @click="retry">Повторить</button>
    </div>
    <NoAccessPage v-if="route.meta.accessDenied" />
    <RouterView v-else />
  </main>
</template>
