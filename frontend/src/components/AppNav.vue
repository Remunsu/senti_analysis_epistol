<script setup>
import { onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import { currentUser, fetchAuthStatus, isAuthenticated, isStaff, logout } from "../auth"

const error = ref("")

async function logoutUser() {
  error.value = ""

  try {
    await logout()
  } catch (err) {
    error.value = err.message || "Не удалось выйти"
  }
}

onMounted(() => {
  fetchAuthStatus().catch(() => {
    error.value = "Не удалось проверить вход"
  })
})
</script>

<template>
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex min-h-14 max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-2">
      <RouterLink
        to="/"
        class="text-base font-semibold text-slate-900 hover:text-slate-600"
      >
        Sentiment Analysis
      </RouterLink>

      <nav class="flex flex-wrap items-center gap-2 text-sm">
        <RouterLink
          to="/works"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Документы
        </RouterLink>
        <RouterLink
          to="/volumes"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Тома
        </RouterLink>
        <RouterLink
          v-if="isStaff"
          to="/upload"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Загрузка XML
        </RouterLink>
        <RouterLink
          v-if="isAuthenticated"
          to="/sentiment/results"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Результаты
        </RouterLink>

        <button
          v-if="isAuthenticated"
          type="button"
          @click="logoutUser"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        >
          Выйти
        </button>
        <RouterLink
          v-else
          to="/login"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Войти
        </RouterLink>
        <RouterLink
          v-if="!isAuthenticated"
          to="/register"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Регистрация
        </RouterLink>

        <span v-if="isAuthenticated" class="ml-2 text-slate-400">
          {{ currentUser?.username }}
        </span>
      </nav>
    </div>
    <div v-if="error" class="mx-auto max-w-7xl px-6 pb-2 text-sm text-red-700">
      {{ error }}
    </div>
  </header>
</template>
