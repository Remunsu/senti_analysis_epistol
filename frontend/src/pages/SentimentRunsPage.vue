<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue"
import { RouterLink } from "vue-router"
import { API_BASE_URL, readApiResponse } from "../api"

const runs = ref([])
const loading = ref(false)
const error = ref("")
let pollTimer = null

const groupedRuns = computed(() => {
  return runs.value.reduce((groups, run) => {
    const dateLabel = formatDate(run.created_at)
    const group = groups.find((item) => item.date === dateLabel)

    if (group) {
      group.runs.push(run)
    } else {
      groups.push({
        date: dateLabel,
        runs: [run],
      })
    }

    return groups
  }, [])
})

const hasRunningRuns = computed(() => {
  return runs.value.some((run) => run.status === "running")
})

const statusLabels = {
  running: "Выполняется",
  completed: "Завершен",
  failed: "Ошибка",
}

function formatDate(value) {
  if (!value) return "Дата не указана"

  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(value))
}

function formatTime(value) {
  if (!value) return ""

  return new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}

function statusClass(status) {
  if (status === "running") return "bg-amber-50 text-amber-700 ring-amber-200"
  if (status === "failed") return "bg-red-50 text-red-700 ring-red-200"

  return "bg-emerald-50 text-emerald-700 ring-emerald-200"
}

function segmentationLabel(run) {
  if (run.max_segment_size) {
    return `Фрагменты ${run.segment_size}-${run.max_segment_size} слов`
  }

  if (run.window_step && run.window_step !== run.segment_size) {
    return `Окна по ${run.segment_size} слов, шаг ${run.window_step}`
  }

  return `Фрагменты по ${run.segment_size} слов`
}

function clearPollTimer() {
  if (!pollTimer) return

  clearTimeout(pollTimer)
  pollTimer = null
}

function schedulePolling() {
  clearPollTimer()

  if (!hasRunningRuns.value) return

  pollTimer = setTimeout(() => {
    fetchRuns({ silent: true })
  }, 3000)
}

async function fetchRuns({ silent = false } = {}) {
  if (!silent) {
    loading.value = true
  }

  error.value = ""

  try {
    const response = await fetch(`${API_BASE_URL}/sentiment/runs/`)
    const data = await readApiResponse(response, "Не удалось загрузить запуски анализа")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить запуски анализа")
    }

    runs.value = data.results || []
    schedulePolling()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
    clearPollTimer()
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRuns()
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
        </div>
      </div>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div v-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загружаю запуски анализа...
      </div>

      <div
        v-else-if="!runs.length"
        class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200"
      >
        Запусков анализа пока нет.
      </div>

      <div v-else class="space-y-6">
        <section
          v-for="group in groupedRuns"
          :key="group.date"
          class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200"
        >
          <div class="border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-semibold text-slate-900">
              {{ group.date }}
            </h2>
          </div>

          <div class="divide-y divide-slate-200">
            <RouterLink
              v-for="run in group.runs"
              :key="run.id"
              :to="{ name: 'sentiment-result-detail', params: { runId: run.id } }"
              class="grid gap-3 px-5 py-4 hover:bg-slate-50 md:grid-cols-[160px_minmax(0,1fr)_160px_160px_auto] md:items-center"
            >
              <div>
                <p class="text-sm text-slate-500">Время</p>
                <p class="font-medium text-slate-900">{{ formatTime(run.created_at) }}</p>
              </div>

              <div>
                <p class="font-medium text-slate-900">
                  {{ run.model_name }}
                </p>
                <p class="mt-1 text-sm text-slate-500">
                  {{ segmentationLabel(run) }}
                </p>
              </div>

              <div>
                <p class="text-sm text-slate-500">Работ</p>
                <p class="font-medium text-slate-900">{{ run.works_count }}</p>
              </div>

              <div>
                <p class="text-sm text-slate-500">Фрагментов</p>
                <p class="font-medium text-slate-900">{{ run.results_count }}</p>
              </div>

              <div class="flex md:justify-end">
                <span
                  class="rounded-full px-3 py-1 text-sm font-medium ring-1"
                  :class="statusClass(run.status)"
                >
                  {{ statusLabels[run.status] || run.status }}
                </span>
              </div>
            </RouterLink>
          </div>
        </section>
      </div>
    </div>
  </main>
</template>
