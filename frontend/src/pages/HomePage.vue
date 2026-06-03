<script setup>
import { computed, onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import { API_BASE_URL } from "../api"
import { currentUser, fetchAuthStatus, isAuthenticated, isStaff } from "../auth"

const authError = ref("")

const isAdmin = computed(() => Boolean(currentUser.value?.is_staff || currentUser.value?.is_superuser))
const adminUrl = computed(() => API_BASE_URL.replace(/\/api\/?$/, "/admin/"))

const pageCards = computed(() => [
  {
    title: "Документы",
    description: "Просмотр, фильтрация, сортировка и выбор произведений для дальнейшего анализа.",
    to: "/works",
    access: "Открытый доступ",
    available: true,
  },
  {
    title: "Тома",
    description: "Список загруженных томов, их свойства и входящие в них произведения. Опциональная загрузка PDF/DJVU.",
    to: "/volumes",
    access: "Открытый доступ",
    available: true,
  },
  {
    title: "Загрузка XML",
    description: "Загрузка XML-файлов томов.",
    to: isStaff.value ? "/upload" : "/login",
    access: isStaff.value ? "Доступно сотруднику" : "Требуются права staff",
    available: isStaff.value,
  },
  {
    title: "Результаты анализа",
    description: "История запусков анализа, таблицы результатов и построение графиков.",
    to: isAuthenticated.value ? "/sentiment/results" : "/login",
    access: isAuthenticated.value ? "Доступно пользователю" : "Требуется авторизация",
    available: isAuthenticated.value,
  },
])

onMounted(() => {
  fetchAuthStatus().catch(() => {
    authError.value = "Не удалось проверить вход"
  })
})
</script>

<template>
  <main class="mx-auto max-w-7xl px-6 py-10">
    <section class="mb-8">
      <h1 class="text-3xl font-semibold text-slate-950 sm:text-4xl">
        Sentiment Analysis
      </h1>
      <p class="mt-4 max-w-3xl text-base leading-7 text-slate-600">
        Система с функционалом загрузки XML-корпуса, просмотра произведений, анализа тональности
        текстов и визуализации результатов по метаданным документов.
      </p>
    </section>

    <section class="grid gap-4 md:grid-cols-3">
      <component
        :is="card.href ? 'a' : RouterLink"
        v-for="card in pageCards"
        :key="card.title"
        :to="card.to"
        :href="card.href"
        :target="card.href ? '_blank' : undefined"
        :rel="card.href ? 'noreferrer' : undefined"
        class="flex min-h-44 cursor-pointer flex-col rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md"
        :class="card.available ? '' : 'opacity-75'"
      >
        <h2 class="text-lg font-semibold text-slate-900">
          {{ card.title }}
        </h2>
        <p class="mt-2 flex-1 text-sm leading-6 text-slate-600">
          {{ card.description }}
        </p>
        <p
          class="mt-4 border-t border-slate-100 pt-3 text-xs font-medium"
          :class="card.available ? 'text-emerald-700' : 'text-amber-700'"
        >
          {{ card.access }}
        </p>
      </component>
    </section>

    <p v-if="authError" class="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-700">
      {{ authError }}
    </p>
  </main>
</template>
