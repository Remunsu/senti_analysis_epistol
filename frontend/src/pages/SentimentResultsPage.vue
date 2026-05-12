<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"

const route = useRoute()

const run = ref(null)
const summary = ref([])
const totals = ref({
  total: 0,
  negative: 0,
  neutral: 0,
  positive: 0,
})
const loading = ref(false)
const error = ref("")
let pollTimer = null

const API_BASE_URL = "http://127.0.0.1:8000/api"

const runId = computed(() => route.params.runId)

function percent(value, total) {
  if (!total) return 0

  return Math.round((value / total) * 100)
}

function scoreClass(score) {
  if (score < -0.15) return "text-red-700"
  if (score > 0.15) return "text-emerald-700"

  return "text-slate-700"
}

function clearPollTimer() {
  if (!pollTimer) return

  clearTimeout(pollTimer)
  pollTimer = null
}

function scheduleResultsPolling() {
  clearPollTimer()

  if (run.value?.status !== "running") return

  pollTimer = setTimeout(() => {
    fetchResults({ silent: true })
  }, 2500)
}

async function readApiResponse(response, fallbackMessage) {
  const contentType = response.headers.get("content-type") || ""

  if (contentType.includes("application/json")) {
    return response.json()
  }

  const text = await response.text()

  return {
    detail: text
      ? `${fallbackMessage}. Сервер вернул не JSON-ответ.`
      : fallbackMessage,
  }
}

async function fetchResults({ silent = false } = {}) {
  if (!silent) {
    loading.value = true
  }

  error.value = ""

  const url = runId.value
    ? `${API_BASE_URL}/sentiment/results/${runId.value}/`
    : `${API_BASE_URL}/sentiment/results/`

  try {
    const response = await fetch(url)
    const data = await readApiResponse(response, "Не удалось загрузить результаты анализа")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить результаты анализа")
    }

    run.value = data.run
    summary.value = data.summary
    totals.value = data.totals || {
      total: 0,
      negative: 0,
      neutral: 0,
      positive: 0,
    }
    scheduleResultsPolling()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
    clearPollTimer()
  } finally {
    loading.value = false
  }
}

watch(runId, () => {
  clearPollTimer()
  fetchResults()
})

onMounted(() => {
  fetchResults()
})

onUnmounted(() => {
  clearPollTimer()
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-slate-900">
            Результаты анализа
          </h1>
          <p v-if="run" class="mt-2 text-slate-600">
            {{ run.model_name }} · фрагменты по {{ run.segment_size }} слов · работ: {{ run.works_count }}
          </p>
          <p
            v-if="run?.status === 'running'"
            class="mt-2 text-sm font-medium text-amber-700"
          >
            Анализ выполняется, результаты обновляются автоматически.
          </p>
          <p
            v-if="run?.status === 'failed'"
            class="mt-2 text-sm font-medium text-red-700"
          >
            Анализ завершился ошибкой: {{ run.error_message || "подробности не указаны" }}
          </p>
        </div>

        <RouterLink
          :to="{ name: 'sentiment-results' }"
          class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          К списку анализов
        </RouterLink>
      </div>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div v-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загружаю результаты...
      </div>

      <template v-else-if="run">
        <section class="mb-6 grid gap-4 md:grid-cols-4">
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Фрагментов</p>
            <p class="mt-2 text-3xl font-bold text-slate-900">{{ totals.total }}</p>
          </div>
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Негативные</p>
            <p class="mt-2 text-3xl font-bold text-red-700">{{ percent(totals.negative, totals.total) }}%</p>
          </div>
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Нейтральные</p>
            <p class="mt-2 text-3xl font-bold text-slate-700">{{ percent(totals.neutral, totals.total) }}%</p>
          </div>
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <p class="text-sm text-slate-500">Позитивные</p>
            <p class="mt-2 text-3xl font-bold text-emerald-700">{{ percent(totals.positive, totals.total) }}%</p>
          </div>
        </section>

        <div
          v-if="run.status === 'running' && !summary.length"
          class="mb-6 rounded-2xl bg-white p-5 text-slate-600 shadow-sm ring-1 ring-slate-200"
        >
          Первые итоги появятся после обработки нескольких писем.
        </div>

        <section class="mb-6 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-semibold text-slate-900">
              Итоги по письмам
            </h2>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full border-collapse text-left">
              <thead class="bg-slate-100 text-sm text-slate-700">
                <tr>
                  <th class="w-[36%] px-5 py-3 font-semibold">Письмо</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Среднее</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Нег.</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Нейтр.</th>
                  <th class="w-[12%] px-5 py-3 font-semibold">Поз.</th>
                  <th class="w-[16%] px-5 py-3 font-semibold">Фрагменты</th>
                </tr>
              </thead>

              <tbody class="divide-y divide-slate-200">
                <tr
                  v-for="item in summary"
                  :key="item.work_id"
                  class="hover:bg-slate-50"
                >
                  <td class="px-5 py-3">
                    <RouterLink
                      :to="{ name: 'work-detail', params: { id: item.work_id } }"
                      class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
                    >
                      {{ item.title || "Без названия" }}
                    </RouterLink>
                    <p class="mt-1 text-sm text-slate-500">
                      {{ item.author || "Автор не указан" }} · {{ item.date || "Дата не указана" }}
                    </p>
                  </td>
                  <td class="px-5 py-3 font-semibold" :class="scoreClass(item.mean_score)">
                    {{ item.mean_score.toFixed(2) }}
                  </td>
                  <td class="px-5 py-3 text-red-700">{{ percent(item.negative_count, item.segments_count) }}%</td>
                  <td class="px-5 py-3 text-slate-700">{{ percent(item.neutral_count, item.segments_count) }}%</td>
                  <td class="px-5 py-3 text-emerald-700">{{ percent(item.positive_count, item.segments_count) }}%</td>
                  <td class="px-5 py-3 text-slate-700">{{ item.segments_count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
