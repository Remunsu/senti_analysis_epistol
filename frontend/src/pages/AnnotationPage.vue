<script setup>
import { computed, onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import { API_BASE_URL } from "../api"

const task = ref(null)
const fragments = ref([])
const genre = ref("письм")
const segmentSize = ref(50)
const loading = ref(false)
const saving = ref(false)
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

async function fetchTask() {
  loading.value = true
  error.value = ""
  success.value = ""
  task.value = null
  fragments.value = []

  const params = new URLSearchParams()

  params.append("genre", genre.value)
  params.append("segment_size", segmentSize.value)

  try {
    const response = await fetch(`${API_BASE_URL}/annotations/task/?${params.toString()}`)
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось получить письмо для разметки")
    }

    task.value = data
    fragments.value = data.fragments
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
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

    success.value = `Сохранено фрагментов: ${data.saved}`
    await fetchTask()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    saving.value = false
  }
}

function setAllLabels(label) {
  fragments.value = fragments.value.map((fragment) => ({
    ...fragment,
    label,
  }))
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
          Одно письмо размечается целиком фрагментами по {{ segmentSize }} слов.
        </p>
      </div>

      <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="grid gap-4 md:grid-cols-[minmax(0,1fr)_180px_auto]">

          <div class="flex items-end">
            <button
              @click="fetchTask"
              :disabled="loading || saving"
              class="w-full rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 md:w-auto">
              Следующее письмо
            </button>
          </div>
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

            <div class="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <div>
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

              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Комментарий
                </label>
                <input
                  v-model="fragment.comment"
                  type="text"
                  class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                />
              </div>
            </div>
          </article>
        </section>

        <div class="sticky bottom-0 mt-6 border-t border-slate-200 bg-slate-50 py-4">
          <div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <p class="text-sm text-slate-600">
              Размечено: {{ labeledCount }} из {{ fragments.length }}
            </p>

            <button
              @click="saveLabels"
              :disabled="saving || !canSave"
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
