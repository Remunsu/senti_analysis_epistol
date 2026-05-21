<script setup>
import { onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { fetchAuthStatus, isAuthenticated, login } from "../auth"

const router = useRouter()
const route = useRoute()

const username = ref("")
const password = ref("")
const submitting = ref(false)
const error = ref("")

async function submitLogin() {
  if (submitting.value) return

  submitting.value = true
  error.value = ""

  try {
    await login(username.value, password.value)
    router.push(typeof route.query.next === "string" ? route.query.next : "/")
  } catch (err) {
    error.value = err.message || "Не удалось войти"
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await fetchAuthStatus()

  if (isAuthenticated.value) {
    router.replace(typeof route.query.next === "string" ? route.query.next : "/")
  }
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-md">
      <h1 class="mb-6 text-3xl font-bold text-slate-900">
        Вход
      </h1>

      <form class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200" @submit.prevent="submitLogin">
        <div class="space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Логин
            </label>
            <input
              v-model="username"
              autocomplete="username"
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Пароль
            </label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            />
          </div>
        </div>

        <div v-if="error" class="mt-4 rounded-xl bg-red-50 p-4 text-red-700">
          {{ error }}
        </div>

        <button
          type="submit"
          :disabled="submitting"
          class="mt-5 rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {{ submitting ? "Вхожу..." : "Войти" }}
        </button>
      </form>
    </div>
  </main>
</template>
