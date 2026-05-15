<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { API_BASE_URL, readApiResponse } from "../api"

const route = useRoute()

const baseline = ref(null)
const candidate = ref(null)
const rows = ref([])
const loading = ref(false)
const error = ref("")
let pollTimer = null

const baselineRunId = computed(() => route.params.baselineRunId)
const candidateRunId = computed(() => route.params.candidateRunId)
const hasRunningRuns = computed(() => {
  return [baseline.value?.run, candidate.value?.run].some((run) => run?.status === "running")
})

const statusLabels = {
  running: "Выполняется",
  completed: "Завершен",
  failed: "Ошибка",
}

function percent(value, total) {
  if (!total) return 0

  return Math.round((value / total) * 100)
}

function deltaLabel(value) {
  const score = Number(value || 0)

  if (score > 0) return `+${score.toFixed(2)}`

  return score.toFixed(2)
}

function deltaClass(value) {
  if (value < -0.15) return "text-red-700"
  if (value > 0.15) return "text-emerald-700"

  return "text-slate-700"
}

function statusClass(status) {
  if (status === "running") return "bg-amber-50 text-amber-700 ring-amber-200"
  if (status === "failed") return "bg-red-50 text-red-700 ring-red-200"

  return "bg-emerald-50 text-emerald-700 ring-emerald-200"
}

function segmentationLabel(run) {
  if (!run) return ""

  if (run.max_segment_size) {
    return `Фрагменты ${run.segment_size}-${run.max_segment_size} слов`
  }

  if (run.window_step && run.window_step !== run.segment_size) {
    return `Окна по ${run.segment_size} слов, шаг ${run.window_step}`
  }

  return `Фрагменты по ${run.segment_size} слов`
}

function metricPercent(metrics, key) {
  if (!metrics) return "—"

  return `${percent(metrics[key], metrics.segments_count)}%`
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
    fetchComparison({ silent: true })
  }, 2500)
}

async function fetchComparison({ silent = false } = {}) {
  if (!silent) {
    loading.value = true
  }

  error.value = ""

  try {
    const response = await fetch(
      `${API_BASE_URL}/sentiment/compare/${baselineRunId.value}/${candidateRunId.value}/`
    )
    const data = await readApiResponse(response, "Не удалось загрузить сравнение")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить сравнение")
    }

    baseline.value = data.baseline
    candidate.value = data.candidate
    rows.value = data.rows || []
    schedulePolling()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
    clearPollTimer()
  } finally {
    loading.value = false
  }
}

watch([baselineRunId, candidateRunId], () => {
  clearPollTimer()
  fetchComparison()
})

onMounted(() => {
  fetchComparison()
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
            Сравнение разбиений
          </h1>
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
        Загружаю сравнение...
      </div>

      <template v-else-if="baseline && candidate">
        <section class="mb-6 grid gap-4 lg:grid-cols-2">
          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-sm text-slate-500">Старый режим</p>
                <p class="mt-1 text-lg font-semibold text-slate-900">
                  {{ segmentationLabel(baseline.run) }}
                </p>
              </div>

              <span
                class="rounded-full px-3 py-1 text-sm font-medium ring-1"
                :class="statusClass(baseline.run.status)"
              >
                {{ statusLabels[baseline.run.status] || baseline.run.status }}
              </span>
            </div>

            <div class="mt-5 grid gap-4 sm:grid-cols-4">
              <div>
                <p class="text-sm text-slate-500">Фрагментов</p>
                <p class="mt-1 text-2xl font-bold text-slate-900">{{ baseline.totals.total }}</p>
              </div>
              <div>
                <p class="text-sm text-slate-500">Нег.</p>
                <p class="mt-1 text-2xl font-bold text-red-700">
                  {{ percent(baseline.totals.negative, baseline.totals.total) }}%
                </p>
              </div>
              <div>
                <p class="text-sm text-slate-500">Нейтр.</p>
                <p class="mt-1 text-2xl font-bold text-slate-700">
                  {{ percent(baseline.totals.neutral, baseline.totals.total) }}%
                </p>
              </div>
              <div>
                <p class="text-sm text-slate-500">Поз.</p>
                <p class="mt-1 text-2xl font-bold text-emerald-700">
                  {{ percent(baseline.totals.positive, baseline.totals.total) }}%
                </p>
              </div>
            </div>

            <RouterLink
              :to="{ name: 'sentiment-result-detail', params: { runId: baseline.run.id } }"
              class="mt-5 inline-block text-sm font-medium text-slate-700 hover:text-slate-900 hover:underline"
            >
              Открыть отдельно
            </RouterLink>
          </div>

          <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-sm text-slate-500">Текущий режим</p>
                <p class="mt-1 text-lg font-semibold text-slate-900">
                  {{ segmentationLabel(candidate.run) }}
                </p>
              </div>

              <span
                class="rounded-full px-3 py-1 text-sm font-medium ring-1"
                :class="statusClass(candidate.run.status)"
              >
                {{ statusLabels[candidate.run.status] || candidate.run.status }}
              </span>
            </div>

            <div class="mt-5 grid gap-4 sm:grid-cols-4">
              <div>
                <p class="text-sm text-slate-500">Фрагментов</p>
                <p class="mt-1 text-2xl font-bold text-slate-900">{{ candidate.totals.total }}</p>
              </div>
              <div>
                <p class="text-sm text-slate-500">Нег.</p>
                <p class="mt-1 text-2xl font-bold text-red-700">
                  {{ percent(candidate.totals.negative, candidate.totals.total) }}%
                </p>
              </div>
              <div>
                <p class="text-sm text-slate-500">Нейтр.</p>
                <p class="mt-1 text-2xl font-bold text-slate-700">
                  {{ percent(candidate.totals.neutral, candidate.totals.total) }}%
                </p>
              </div>
              <div>
                <p class="text-sm text-slate-500">Поз.</p>
                <p class="mt-1 text-2xl font-bold text-emerald-700">
                  {{ percent(candidate.totals.positive, candidate.totals.total) }}%
                </p>
              </div>
            </div>

            <RouterLink
              :to="{ name: 'sentiment-result-detail', params: { runId: candidate.run.id } }"
              class="mt-5 inline-block text-sm font-medium text-slate-700 hover:text-slate-900 hover:underline"
            >
              Открыть отдельно
            </RouterLink>
          </div>
        </section>

        <section class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="border-b border-slate-200 px-5 py-4">
            <h2 class="text-lg font-semibold text-slate-900">
              По произведениям
            </h2>
          </div>

          <div class="overflow-x-auto">
            <table class="min-w-[1080px] border-collapse text-left">
              <thead class="bg-slate-100 text-sm text-slate-700">
                <tr>
                  <th class="px-5 py-3 font-semibold">Произведение</th>
                  <th class="px-5 py-3 font-semibold">Дата</th>
                  <th class="px-5 py-3 font-semibold">50 слов</th>
                  <th class="px-5 py-3 font-semibold">60-120 слов</th>
                  <th class="px-5 py-3 font-semibold">Разница среднего</th>
                  <th class="px-5 py-3 font-semibold">Разница фрагментов</th>
                </tr>
              </thead>

              <tbody class="divide-y divide-slate-200">
                <tr
                  v-for="row in rows"
                  :key="row.original_work_id"
                  class="hover:bg-slate-50"
                >
                  <td class="px-5 py-3">
                    <RouterLink
                      v-if="row.work_id"
                      :to="{ name: 'work-detail', params: { id: row.work_id } }"
                      class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
                    >
                      {{ row.title || "Без названия" }}
                    </RouterLink>
                    <span v-else class="font-medium text-slate-900">
                      {{ row.title || "Без названия" }}
                    </span>
                  </td>

                  <td class="px-5 py-3 text-sm text-slate-700">
                    {{ row.date || "—" }}
                  </td>

                  <td class="px-5 py-3 text-sm text-slate-700">
                    <template v-if="row.baseline">
                      Нег. {{ metricPercent(row.baseline, "negative_count") }},
                      нейтр. {{ metricPercent(row.baseline, "neutral_count") }},
                      поз. {{ metricPercent(row.baseline, "positive_count") }}
                      · {{ row.baseline.segments_count }}
                    </template>
                    <span v-else>—</span>
                  </td>

                  <td class="px-5 py-3 text-sm text-slate-700">
                    <template v-if="row.candidate">
                      Нег. {{ metricPercent(row.candidate, "negative_count") }},
                      нейтр. {{ metricPercent(row.candidate, "neutral_count") }},
                      поз. {{ metricPercent(row.candidate, "positive_count") }}
                      · {{ row.candidate.segments_count }}
                    </template>
                    <span v-else>—</span>
                  </td>

                  <td class="px-5 py-3 text-sm font-semibold" :class="deltaClass(row.mean_score_delta)">
                    {{ deltaLabel(row.mean_score_delta) }}
                  </td>

                  <td class="px-5 py-3 text-sm text-slate-700">
                    {{ row.segments_delta > 0 ? "+" : "" }}{{ row.segments_delta }}
                  </td>
                </tr>

                <tr v-if="rows.length === 0">
                  <td colspan="6" class="px-5 py-8 text-center text-slate-500">
                    Результаты еще не появились.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
