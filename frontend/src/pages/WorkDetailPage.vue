<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { API_BASE_URL } from "../api"

const route = useRoute()

const work = ref(null)
const loading = ref(false)
const error = ref("")
const selectedSource = ref("text")

const workId = computed(() => route.params.id)

const displayedContent = computed(() => {
  if (!work.value) return ""

  return selectedSource.value === "xml" ? work.value.raw_xml || "" : work.value.plain_text || ""
})

const properties = computed(() => {
  if (!work.value) return []

  return [
    ["ID источника", work.value.source_id],
    ["Том", work.value.volume_title || work.value.volume],
    ["Номер", work.value.number],
    ["Название", work.value.title],
    ["Краткое название", work.value.title_short],
    ["Описание", work.value.title_desc],
    ["Автор", work.value.author],
    ["Жанр", work.value.genre],
    ["Дата", work.value.date],
    ["Страницы", work.value.pages],
    ["Место", work.value.place],
    ["Язык", work.value.language],
    ["Примечание", work.value.note],
    ["Создано", formatDateTime(work.value.created_at)],
  ].filter(([, value]) => hasPropertyValue(value))
})

function hasPropertyValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== ""
}

function formatDateTime(value) {
  if (!value) return ""

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

async function fetchWork() {
  loading.value = true
  error.value = ""

  try {
    const response = await fetch(`${API_BASE_URL}/works/${workId.value}/`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить произведение")
    }

    work.value = await response.json()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

watch(workId, () => {
  fetchWork()
})

onMounted(() => {
  fetchWork()
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div class="mb-3 flex flex-wrap gap-3 text-sm">
            <RouterLink
              to="/"
              class="font-medium text-slate-600 hover:text-slate-900"
            >
              Назад к произведениям
            </RouterLink>

            <RouterLink
              v-if="work?.volume"
              :to="{ name: 'volume-detail', params: { id: work.volume } }"
              class="font-medium text-slate-600 hover:text-slate-900"
            >
              К тому
            </RouterLink>
          </div>

          <h1 class="mt-3 text-3xl font-bold text-slate-900">
            {{ work?.title || "Произведение" }}
          </h1>

          <p v-if="work?.title_short" class="mt-2 text-slate-600">
            <RouterLink :to="{ name: 'volume-detail', params: { id: work.volume } }" class="font-medium text-slate-900 hover:text-slate-600 hover:underline">
              {{ work.title_short }}
            </RouterLink>
          </p>
        </div>
      </div>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div v-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загрузка произведения...
      </div>

      <template v-else-if="work">
        <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <dl class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div
              v-for="[label, value] in properties"
              :key="label"
              class="min-w-0 border-b border-slate-100 pb-3"
            >
              <dt class="text-xs font-semibold uppercase text-slate-500">
                {{ label }}
              </dt>
              <dd class="mt-1 break-words text-sm text-slate-900">
                {{ value }}
              </dd>
            </div>
          </dl>
        </section>

        <section class="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-semibold text-slate-900">
              Содержимое
            </h2>

            <div class="flex rounded-xl border border-slate-300 bg-white p-1">
              <button
                type="button"
                @click="selectedSource = 'text'"
                :class="[
                  'rounded-lg px-4 py-2 text-sm font-medium',
                  selectedSource === 'text'
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-700 hover:bg-slate-100',
                ]"
              >
                Текст
              </button>

              <button
                type="button"
                @click="selectedSource = 'xml'"
                :class="[
                  'rounded-lg px-4 py-2 text-sm font-medium',
                  selectedSource === 'xml'
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-700 hover:bg-slate-100',
                ]"
              >
                XML
              </button>
            </div>
          </div>

          <textarea
            readonly
            :value="displayedContent"
            class="min-h-96 w-full resize-y border-0 bg-white p-5 font-mono text-sm leading-6 text-slate-900 outline-none"
          />
        </section>
      </template>
    </div>
  </main>
</template>
