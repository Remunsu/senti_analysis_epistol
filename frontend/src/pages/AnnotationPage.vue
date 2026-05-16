<script setup>
import { computed, onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import { API_BASE_URL } from "../api"

const task = ref(null)
const fragments = ref([])
const criteria = ref({
  genre: "письмо",
  languages: ["ru", "de ru", "la ru"],
  min_segment_size: 60,
  max_segment_size: 120,
})
const stats = ref({
  total_count: 0,
  labeled_count: 0,
  skipped_count: 0,
  remaining_count: 0,
  labeled_fragments_count: 0,
  remaining_fragments_count: 0,
})
const loading = ref(false)
const saving = ref(false)
const skipping = ref(false)
const exporting = ref(false)
const error = ref("")
const success = ref("")

const labelOptions = [
  { value: "-1", label: "Негативная" },
  { value: "0", label: "Нейтральная" },
  { value: "1", label: "Позитивная" },
]

const labeledCount = computed(() => {
  return fragments.value.filter((fragment) => fragment.label).length
})

const canSave = computed(() => {
  return task.value && fragments.value.length > 0 && labeledCount.value === fragments.value.length
})

async function fetchTask(options = {}) {
  const { clearMessages = true } = options

  loading.value = true
  if (clearMessages) {
    error.value = ""
    success.value = ""
  }
  task.value = null
  fragments.value = []

  try {
    const response = await fetch(`${API_BASE_URL}/annotations/task/`)
    const data = await response.json()
    applyAnnotationMeta(data)

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось получить письмо для разметки")
    }

    if (!data.work) {
      success.value = data.detail || "Все подходящие письма уже размечены"
      return
    }

    task.value = data
    fragments.value = data.fragments || []
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

function applyAnnotationMeta(data) {
  if (data.criteria) {
    criteria.value = data.criteria
  }

  stats.value = {
    total_count: Number(data.total_count) || 0,
    labeled_count: Number(data.labeled_count) || 0,
    skipped_count: Number(data.skipped_count) || 0,
    remaining_count: Number(data.remaining_count) || 0,
    labeled_fragments_count: Number(data.labeled_fragments_count) || 0,
    remaining_fragments_count: Number(data.remaining_fragments_count) || 0,
  }
}

async function saveLabels() {
  if (!canSave.value) {
    error.value = "Разметьте все фрагменты письма"
    return
  }

  saving.value = true
  error.value = ""
  success.value = ""

  try {
    const response = await fetch(`${API_BASE_URL}/annotations/task/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        work_id: task.value.work.id,
        fragments: fragments.value,
      }),
    })
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось сохранить разметку")
    }

    applyAnnotationMeta(data)
    success.value = `Сохранено фрагментов: ${data.saved}`
    await fetchTask({ clearMessages: false })
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    saving.value = false
  }
}

async function skipWork() {
  if (!task.value || skipping.value) return
  if (!window.confirm("Пропустить это письмо и не включать его в CSV?")) return

  skipping.value = true
  error.value = ""
  success.value = ""

  try {
    const response = await fetch(`${API_BASE_URL}/annotations/skip/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        work_id: task.value.work.id,
      }),
    })
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось пропустить письмо")
    }

    applyAnnotationMeta(data)
    success.value = "Письмо пропущено"
    await fetchTask({ clearMessages: false })
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    skipping.value = false
  }
}

function setAllLabels(label) {
  fragments.value = fragments.value.map((fragment) => ({
    ...fragment,
    label,
  }))
}

async function exportLabels() {
  exporting.value = true
  error.value = ""

  try {
    const response = await fetch(`${API_BASE_URL}/annotations/export/`)

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || "Не удалось экспортировать разметку")
    }

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")

    link.href = url
    link.download = `sentiment_annotations_${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchTask()
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-900">
          Разметка писем
        </h1>
        <p class="mt-2 text-slate-600">
          Жанр: {{ criteria.genre }}. Языки: {{ criteria.languages.join(", ") }}. Фрагменты: {{ criteria.min_segment_size }}-{{ criteria.max_segment_size }} слов.
        </p>
      </div>

      <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <div class="rounded-xl border border-slate-200 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">
              Всего подходит
            </p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">
              {{ stats.total_count }}
            </p>
          </div>

          <div class="rounded-xl border border-slate-200 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">
              Размечено
            </p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">
              {{ stats.labeled_count }}
            </p>
          </div>

          <div class="rounded-xl border border-slate-200 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">
              Пропущено
            </p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">
              {{ stats.skipped_count }}
            </p>
          </div>

          <div class="rounded-xl border border-slate-200 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">
              Осталось
            </p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">
              {{ stats.remaining_count }}
            </p>
          </div>

          <div class="rounded-xl border border-slate-200 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">
              Фрагментов размечено
            </p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">
              {{ stats.labeled_fragments_count }}
            </p>
          </div>

          <div class="rounded-xl border border-slate-200 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">
              Фрагментов осталось
            </p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">
              {{ stats.remaining_fragments_count }}
            </p>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            @click="fetchTask"
            :disabled="loading || saving || skipping"
            class="rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40">
            Следующее письмо
          </button>

          <button
            @click="exportLabels"
            :disabled="exporting"
            class="rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40">
            {{ exporting ? "Экспортирую..." : "Экспорт CSV" }}
          </button>
        </div>
      </section>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div v-if="success" class="mb-4 rounded-xl bg-emerald-50 p-4 text-emerald-700">
        {{ success }}
      </div>

      <div v-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загружаю письмо для разметки...
      </div>

      <template v-else-if="task">
        <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 class="text-xl font-semibold text-slate-900">
                {{ task.work.title || "Без названия" }}
              </h2>
              <p class="mt-2 text-sm text-slate-600">
                {{ task.work.author || "Автор не указан" }} · {{ task.work.date || "Дата не указана" }} · {{ task.work.genre || "Жанр не указан" }}
              </p>
            </div>

            <RouterLink
              :to="{ name: 'work-detail', params: { id: task.work.id } }"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Открыть письмо
            </RouterLink>
          </div>

          <div class="mt-4 flex flex-wrap items-center gap-3">
            <p class="text-sm text-slate-600">
              Размечено: {{ labeledCount }} из {{ fragments.length }}
            </p>

            <button
              v-for="option in labelOptions"
              :key="option.value"
              @click="setAllLabels(option.value)"
              class="rounded-xl border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Все: {{ option.label }}
            </button>
          </div>
        </section>

        <section class="space-y-4">
          <article
            v-for="fragment in fragments"
            :key="fragment.segment_index"
            class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200"
          >
            <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-slate-900">
                Фрагмент {{ fragment.segment_index + 1 }}
              </h3>
              <p class="text-sm text-slate-500">
                Слова {{ fragment.word_start + 1 }}-{{ fragment.word_end }}
              </p>
            </div>

            <p class="whitespace-pre-wrap text-slate-900">
              {{ fragment.text }}
            </p>

            <div class="mt-4 max-w-sm">
              <label class="mb-1 block text-sm font-medium text-slate-700">
                Тональность
              </label>
              <select
                v-model="fragment.label"
                class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
              >
                <option value="">Не выбрана</option>
                <option
                  v-for="option in labelOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>
          </article>
        </section>

        <div class="sticky bottom-0 mt-6 border-t border-slate-200 bg-slate-50 py-4">
          <div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <p class="text-sm text-slate-600">
              Размечено: {{ labeledCount }} из {{ fragments.length }}
            </p>

            <button
              @click="skipWork"
              :disabled="saving || skipping"
              class="rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {{ skipping ? "Пропускаю..." : "Пропустить и не включать в CSV" }}
            </button>

            <button
              @click="saveLabels"
              :disabled="saving || skipping || !canSave"
              class="rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {{ saving ? "Сохраняю..." : "Сохранить письмо и перейти дальше" }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </main>
</template>
