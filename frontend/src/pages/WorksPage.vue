<script setup>
import { onMounted, ref, watch } from "vue"

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

const API_BASE_URL = "http://127.0.0.1:8000/api"

async function fetchVolumes() {
  const response = await fetch(`${API_BASE_URL}/volumes/`)

  if (!response.ok) {
    throw new Error("Не удалось загрузить тома")
  }

  volumes.value = await response.json()
}

async function fetchFilterOptions() {
  const response = await fetch(`${API_BASE_URL}/works/filters/`)

  if (!response.ok) {
    throw new Error("Не удалось загрузить фильтры")
  }

  filterOptions.value = await response.json()
}

async function fetchWorks() {
  loading.value = true
  error.value = ""

  const params = new URLSearchParams()

  if (search.value) params.append("search", search.value)
  if (selectedVolume.value) params.append("volume", selectedVolume.value)
  if (selectedGenre.value) params.append("genre", selectedGenre.value)
  if (ordering.value) params.append("ordering", ordering.value)

  try {
    const response = await fetch(`${API_BASE_URL}/works/?${params.toString()}`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить произведения")
    }

    works.value = await response.json()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  search.value = ""
  selectedVolume.value = ""
  selectedGenre.value = ""
  ordering.value = "id"
  fetchWorks()
}

watch(
  [selectedVolume, selectedGenre, ordering],
  () => {
    fetchWorks()
  }
)

onMounted(async () => {
  try {
    await fetchVolumes()
    await fetchFilterOptions()
    await fetchWorks()
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
      </div>

      <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="grid gap-4 md:grid-cols-5">
          <div class="md:col-span-2">
            <label class="mb-1 block text-sm font-medium text-slate-700">
              Поиск
            </label>
            <input
              v-model="search"
              @keyup.enter="fetchWorks"
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
            @click="fetchWorks"
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
        <div class="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <p class="text-sm text-slate-600">
            Найдено: {{ works.length }}
          </p>

          <p v-if="loading" class="text-sm text-slate-500">
            Обновление таблицы...
          </p>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full table-fixed border-collapse text-left">
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
                  <span class="px-3 py-1 text-sm text-slate-700">
                    {{ work.genre || "—" }}
                  </span>
                </td>

                <td class="px-5 py-4 text-slate-700">
                  <span v-if="work.date">
                    {{ work.date }}
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
      </section>
    </div>
  </main>
</template>
