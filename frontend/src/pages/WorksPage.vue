<script setup>
import { computed, onMounted, ref, watch } from "vue"

const works = ref([])
const volumes = ref([])

const filterOptions = ref({
  genres: [],
  authors: [],
  languages: [],
  places: [],
})

const search = ref("")
const selectedVolume = ref("")
const selectedGenre = ref("")
const ordering = ref("id")

const loading = ref(false)
const error = ref("")

const currentPage = ref(1)
const totalCount = ref(0)
const nextPageUrl = ref(null)
const previousPageUrl = ref(null)

const pageSize = 50

const API_BASE_URL = "http://127.0.0.1:8000/api"

const totalPages = computed(() => {
  if (!totalCount.value) return 1
  return Math.ceil(totalCount.value / pageSize)
})

async function fetchVolumes() {
  const response = await fetch(`${API_BASE_URL}/volumes/`)

  if (!response.ok) {
    throw new Error("Не удалось загрузить тома")
  }

  const data = await response.json()

  // Если volumes тоже пагинируются, берём results.
  volumes.value = Array.isArray(data) ? data : data.results
}

async function fetchFilterOptions() {
  const response = await fetch(`${API_BASE_URL}/works/filters/`)

  if (!response.ok) {
    throw new Error("Не удалось загрузить фильтры")
  }

  filterOptions.value = await response.json()
}

async function fetchWorks(page = 1) {
  loading.value = true
  error.value = ""

  const params = new URLSearchParams()

  params.append("page", page)

  if (search.value) params.append("search", search.value)
  if (selectedVolume.value) params.append("volume", selectedVolume.value)
  if (selectedGenre.value) params.append("genre", selectedGenre.value)
  if (ordering.value) params.append("ordering", ordering.value)

  try {
    const response = await fetch(`${API_BASE_URL}/works/?${params.toString()}`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить произведения")
    }

    const data = await response.json()

    // DRF с пагинацией возвращает объект:
    // { count, next, previous, results }
    if (Array.isArray(data)) {
      works.value = data
      totalCount.value = data.length
      nextPageUrl.value = null
      previousPageUrl.value = null
      currentPage.value = 1
    } else {
      works.value = data.results
      totalCount.value = data.count
      nextPageUrl.value = data.next
      previousPageUrl.value = data.previous
      currentPage.value = page
    }
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  currentPage.value = 1
  fetchWorks(1)
}

function resetFilters() {
  search.value = ""
  selectedVolume.value = ""
  selectedGenre.value = ""
  ordering.value = "id"

  currentPage.value = 1
  fetchWorks(1)
}

function goToPage(page) {
  if (page < 1 || page > totalPages.value || loading.value) return

  fetchWorks(page)
}

function goToPreviousPage() {
  if (!previousPageUrl.value || loading.value) return

  fetchWorks(currentPage.value - 1)
}

function goToNextPage() {
  if (!nextPageUrl.value || loading.value) return

  fetchWorks(currentPage.value + 1)
}

watch(
  [selectedVolume, selectedGenre, ordering],
  () => {
    applyFilters()
  }
)

onMounted(async () => {
  try {
    await fetchVolumes()
    await fetchFilterOptions()
    await fetchWorks(1)
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  }
})
</script>

<template>
  <main class="min-h-screen bg-slate-50 p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-900">
          Произведения
        </h1>
        <p class="mt-2 text-slate-600">
          Просмотр, поиск, фильтрация и сортировка корпуса.
        </p>
      </div>

      <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="grid gap-4 md:grid-cols-5">
          <div class="md:col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Поиск
            </label>
            <input
              v-model="search"
              @keyup.enter="applyFilters"
              type="text"
              placeholder="Название или текст..."
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Том
            </label>
            <select
              v-model="selectedVolume"
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            >
              <option value="">Все тома</option>
              <option
                v-for="volume in volumes"
                :key="volume.id"
                :value="volume.id"
              >
                {{ volume.title_short || volume.title }}
              </option>
            </select>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Жанр
            </label>
            <select
              v-model="selectedGenre"
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            >
              <option value="">Все жанры</option>
              <option
                v-for="genre in filterOptions.genres"
                :key="genre"
                :value="genre"
              >
                {{ genre }}
              </option>
            </select>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Сортировка
            </label>
            <select
              v-model="ordering"
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            >
              <option value="id">По добавлению</option>
              <option value="title">Название А–Я</option>
              <option value="-title">Название Я–А</option>
              <option value="date_from">Дата ↑</option>
              <option value="-date_from">Дата ↓</option>
              <option value="genre">Жанр</option>
              <option value="page_number">Страница</option>
            </select>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            @click="applyFilters"
            class="rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700"
          >
            Найти
          </button>

          <button
            @click="resetFilters"
            class="rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100"
          >
            Сбросить
          </button>
        </div>
      </section>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <section class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <p class="text-sm text-slate-600">
            Найдено: {{ totalCount }}
          </p>

          <p v-if="loading" class="text-sm text-slate-500">
            Обновление таблицы...
          </p>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-left">
            <thead class="bg-slate-100 text-sm text-slate-700">
              <tr>
                <th class="w-[35%] px-5 py-3 font-semibold">Название</th>
                <th class="w-[15%] px-5 py-3 font-semibold">Автор</th>
                <th class="w-[20%] px-5 py-3 font-semibold">Жанр</th>
                <th class="w-[15%] px-5 py-3 font-semibold">Дата</th>
                <th class="w-[15%] px-5 py-3 font-semibold">Том</th>
              </tr>
            </thead>

            <tbody class="divide-y divide-slate-200">
              <tr
                v-for="work in works"
                :key="work.id"
                class="hover:bg-slate-50"
              >
                <td class="max-w-md px-5 py-4">
                  <div class="font-medium text-slate-900">
                    {{ work.title }}
                  </div>
                  <div v-if="work.title_short" class="mt-1 text-sm text-slate-500">
                    {{ work.title_short }}
                  </div>
                </td>

                <td class="px-5 py-4 text-slate-700">
                  {{ work.author || "—" }}
                </td>

                <td class="px-5 py-4">
                  <span class="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
                    {{ work.genre || "—" }}
                  </span>
                </td>

                <td class="px-5 py-4 text-slate-700">
                  <span v-if="work.date_from || work.date_to">
                    {{ work.date_from }}<span v-if="work.date_to">–{{ work.date_to }}</span>
                  </span>
                  <span v-else>—</span>
                </td>

                <td class="px-5 py-4 text-slate-700">
                  {{ work.volume_title || "—" }}
                </td>
              </tr>

              <tr v-if="!loading && works.length === 0">
                <td colspan="6" class="px-5 py-8 text-center text-slate-500">
                  Произведения не найдены
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-4">
          <p class="text-sm text-slate-600">
            Страница {{ currentPage }} из {{ totalPages }}
          </p>

          <div class="flex items-center gap-2">
            <button
              @click="goToPreviousPage"
              :disabled="!previousPageUrl || loading"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Назад
            </button>

            <button
              v-if="currentPage > 2"
              @click="goToPage(1)"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              1
            </button>

            <span v-if="currentPage > 3" class="px-2 text-slate-500">
              ...
            </span>

            <button
              v-if="currentPage > 1"
              @click="goToPage(currentPage - 1)"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {{ currentPage - 1 }}
            </button>

            <button
              class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
            >
              {{ currentPage }}
            </button>

            <button
              v-if="currentPage < totalPages"
              @click="goToPage(currentPage + 1)"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {{ currentPage + 1 }}
            </button>

            <span v-if="currentPage < totalPages - 2" class="px-2 text-slate-500">
              ...
            </span>

            <button
              v-if="currentPage < totalPages - 1"
              @click="goToPage(totalPages)"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              {{ totalPages }}
            </button>

            <button
              @click="goToNextPage"
              :disabled="!nextPageUrl || loading"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Вперёд
            </button>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>
