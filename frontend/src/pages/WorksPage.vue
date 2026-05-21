<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { API_BASE_URL, readApiResponse } from "../api"
import { authFetch, fetchAuthStatus, isAuthenticated } from "../auth"
import AutocompleteInput from "../components/AutocompleteInput.vue"
import PaginationControls from "../components/PaginationControls.vue"
import WorksTable from "../components/WorksTable.vue"

const router = useRouter()

const works = ref([])
const volumes = ref([])

const filterOptions = ref({
  genres: [],
  authors: [],
  recipients: [],
  languages: [],
  places: [],
  dates: [],
  numbers: [],
})

const search = ref("")
const ordering = ref("id")
const filterRows = ref([])

const loading = ref(false)
const analyzing = ref(false)
const error = ref("")

const currentPage = ref(1)
const totalCount = ref(0)
const nextPageUrl = ref(null)
const previousPageUrl = ref(null)
const selectedWorkIds = ref(new Set())
const allFilteredSelected = ref(false)

const pageSize = 50
let nextFilterId = 1

const STORAGE_KEY = "sentiment-app:works-page-state"
let orderingWatcherReady = false

const filterFields = [
  { key: "volume", label: "Том" },
  { key: "author", label: "Автор" },
  { key: "recipient", label: "Адресат" },
  { key: "genre", label: "Жанр" },
  { key: "language", label: "Язык" },
  { key: "place", label: "Место" },
  { key: "date", label: "Дата" },
  { key: "number", label: "Номер" },
]

const rangeFilterKeys = new Set(["date", "number"])

const filterFieldOptions = filterFields.map((field) => ({
  label: field.label,
  value: field.key,
}))

const totalPages = computed(() => {
  if (!totalCount.value) return 1
  return Math.ceil(totalCount.value / pageSize)
})

const selectedWorksCount = computed(() => {
  if (allFilteredSelected.value) return totalCount.value

  return selectedWorkIds.value.size
})

function clearSelection() {
  selectedWorkIds.value = new Set()
  allFilteredSelected.value = false
  savePageState()
}

function normalizeAutocompleteValue(value) {
  return String(value || "").trim().toLowerCase()
}

function getFilterField(fieldInput) {
  const normalizedInput = normalizeAutocompleteValue(fieldInput)

  return filterFields.find((field) => {
    return (
      normalizeAutocompleteValue(field.label) === normalizedInput ||
      normalizeAutocompleteValue(field.key) === normalizedInput
    )
  })
}

function getFilterValueOptions(fieldInput) {
  const field = getFilterField(fieldInput)

  if (!field) return []

  if (field.key === "volume") {
    return volumes.value.map((volume) => ({
      label: volume.title_short || volume.title || `Том ${volume.id}`,
      value: String(volume.id),
    }))
  }

  const optionMap = {
    author: filterOptions.value.authors,
    recipient: filterOptions.value.recipients,
    genre: filterOptions.value.genres,
    language: filterOptions.value.languages,
    place: filterOptions.value.places,
    date: filterOptions.value.dates,
    number: filterOptions.value.numbers,
  }

  return (optionMap[field.key] || []).map((value) => ({
    label: String(value),
    value: String(value),
  }))
}

function isRangeFilter(fieldInput) {
  const field = getFilterField(fieldInput)

  return field ? rangeFilterKeys.has(field.key) : false
}

function isNumberRangeFilter(fieldInput) {
  return getFilterField(fieldInput)?.key === "number"
}

function resolveFilterInput(fieldInput, value) {
  const rawValue = String(value || "").trim()
  const normalizedValue = normalizeAutocompleteValue(rawValue)
  const option = getFilterValueOptions(fieldInput).find((item) => {
    return (
      normalizeAutocompleteValue(item.label) === normalizedValue ||
      normalizeAutocompleteValue(item.value) === normalizedValue
    )
  })

  return option ? option.value : rawValue
}

function resetFilterRowValues(row) {
  row.value = ""
  row.from = ""
  row.to = ""
  savePageState()
}

function addFilterRow() {
  filterRows.value.push({
    id: nextFilterId,
    field: "",
    value: "",
    from: "",
    to: "",
  })
  nextFilterId += 1
  savePageState()
}

function removeFilterRow(filterId) {
  filterRows.value = filterRows.value.filter((row) => row.id !== filterId)
  savePageState()
}

function clearFilterRows() {
  filterRows.value = []
  savePageState()
}

function hasVolumeFilterValue() {
  return filterRows.value.some((row) => {
    return getFilterField(row.field)?.key === "volume" && String(row.value || "").trim()
  })
}

function savePageState() {
  const state = {
    search: search.value,
    ordering: ordering.value,
    filterRows: filterRows.value,
    currentPage: currentPage.value,
    totalCount: totalCount.value,
    nextPageUrl: nextPageUrl.value,
    previousPageUrl: previousPageUrl.value,
    selectedWorkIds: [...selectedWorkIds.value],
    allFilteredSelected: allFilteredSelected.value,
    works: works.value,
  }

  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

function restorePageState() {
  const rawState = sessionStorage.getItem(STORAGE_KEY)

  if (!rawState) return false

  try {
    const state = JSON.parse(rawState)
    const restoredFilterRows = Array.isArray(state.filterRows)
      ? state.filterRows.map((row) => ({
        ...row,
        field: row.field === "page_number" || row.field === "Страница" ? "number" : row.field,
      }))
      : []

    search.value = state.search || ""
    ordering.value = normalizeOrderingValue(state.ordering)
    filterRows.value = restoredFilterRows
    currentPage.value = Number(state.currentPage) || 1
    totalCount.value = Number(state.totalCount) || 0
    nextPageUrl.value = state.nextPageUrl || null
    previousPageUrl.value = state.previousPageUrl || null
    selectedWorkIds.value = new Set(Array.isArray(state.selectedWorkIds) ? state.selectedWorkIds : [])
    allFilteredSelected.value = Boolean(state.allFilteredSelected)
    works.value = Array.isArray(state.works) ? state.works : []
    nextFilterId = restoredFilterRows.reduce((maxId, row) => Math.max(maxId, Number(row.id) || 0), 0) + 1

    return true
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
    return false
  }
}

function normalizeOrderingValue(value) {
  if (value === "date" || value === "date_from") return "date_from,date_to,number"
  if (value === "-date" || value === "-date_from") return "-date_from,-date_to,number"
  if (value === "page_number") return "number"

  return value || "id"
}

async function fetchVolumes() {
  const response = await fetch(`${API_BASE_URL}/volumes/`)

  if (!response.ok) {
    throw new Error("Не удалось загрузить тома")
  }

  const data = await response.json()

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

  const params = buildWorkParams(page)

  try {
    const response = await fetch(`${API_BASE_URL}/works/?${params.toString()}`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить произведения")
    }

    const data = await response.json()

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

    savePageState()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

function buildWorkParams(page = null) {
  const params = new URLSearchParams()

  if (page) params.append("page", page)

  if (search.value) params.append("search", search.value)
  if (ordering.value) params.append("ordering", ordering.value)

  filterRows.value.forEach((row) => {
    const field = getFilterField(row.field)

    if (!field) return

    if (isRangeFilter(row.field)) {
      const from = resolveFilterInput(row.field, row.from)
      const to = resolveFilterInput(row.field, row.to)

      if (from || to) {
        params.append(`${field.key}_range`, `${from}..${to}`)
      }

      return
    }

    const value = resolveFilterInput(row.field, row.value)

    if (value) {
      params.append(field.key, value)
    }
  })

  return params
}

function buildAnalysisFilterParams() {
  const params = buildWorkParams()

  params.delete("ordering")

  return params
}

async function analyzeSelectedWorks() {
  if (!isAuthenticated.value || !selectedWorksCount.value || analyzing.value) return

  analyzing.value = true
  error.value = ""

  try {
    const response = await authFetch(`${API_BASE_URL}/sentiment/analyze/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildAnalysisRequestBody()),
    })
    const data = await readApiResponse(response, "Не удалось выполнить анализ")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось выполнить анализ")
    }

    router.push({ name: "sentiment-result-detail", params: { runId: data.run.id } })
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    analyzing.value = false
  }
}

function buildAnalysisRequestBody() {
  return {
    all_filtered: allFilteredSelected.value,
    filters_query: allFilteredSelected.value ? buildAnalysisFilterParams().toString() : "",
    work_ids: allFilteredSelected.value ? [] : [...selectedWorkIds.value],
  }
}

function applyFilters() {
  currentPage.value = 1
  clearSelection()
  fetchWorks(1)
}

function resetFilters() {
  search.value = ""
  ordering.value = "id"
  clearFilterRows()

  currentPage.value = 1
  clearSelection()
  fetchWorks(1)
}

function toggleWorkSelection(workId) {
  if (allFilteredSelected.value) return

  const nextSelectedIds = new Set(selectedWorkIds.value)

  if (nextSelectedIds.has(workId)) {
    nextSelectedIds.delete(workId)
  } else {
    nextSelectedIds.add(workId)
  }

  selectedWorkIds.value = nextSelectedIds
  savePageState()
}

function toggleAllFilteredWorks() {
  if (allFilteredSelected.value) {
    clearSelection()
    return
  }

  selectAllFilteredWorks()
}

function selectAllFilteredWorks() {
  if (!totalCount.value) return

  selectedWorkIds.value = new Set()
  allFilteredSelected.value = true
  savePageState()
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

watch(ordering, () => {
  if (!orderingWatcherReady) {
    savePageState()
    return
  }

  applyFilters()
})

watch(search, () => {
  savePageState()
})

watch(filterRows, () => {
  savePageState()
}, { deep: true })

onMounted(async () => {
  try {
    await fetchAuthStatus()

    const restored = restorePageState()

    if (!isAuthenticated.value) {
      clearSelection()
    }
    const page = restored ? currentPage.value : 1

    if (restored && hasVolumeFilterValue()) {
      await fetchVolumes()
      await Promise.all([
        fetchWorks(page),
        fetchFilterOptions(),
      ])
    } else {
      await Promise.all([
        fetchWorks(page),
        fetchVolumes(),
        fetchFilterOptions(),
      ])
    }

    orderingWatcherReady = true
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
    orderingWatcherReady = true
  }
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-900">
          Произведения
        </h1>
      </div>

      <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="grid gap-4 md:grid-cols-[minmax(0,1fr)_240px]">
          <div>
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
              Сортировка
            </label>
            <select
              v-model="ordering"
              class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
            >
              <option value="id">По добавлению</option>
              <option value="title">Название А–Я</option>
              <option value="-title">Название Я–А</option>
              <option value="date_from,date_to,number">Дата ↑</option>
              <option value="-date_from,-date_to,number">Дата ↓</option>
              <option value="genre">Жанр</option>
              <option value="number">Номер</option>
            </select>
          </div>
        </div>

        <div class="mt-4 border-t border-slate-200 pt-4">
          <div class="mb-3">
            <h2 class="text-sm font-semibold text-slate-900">
              Фильтры
            </h2>
          </div>

          <div v-if="filterRows.length" class="space-y-3">
            <div
              v-for="row in filterRows"
              :key="row.id"
              class="grid gap-3 md:grid-cols-[minmax(0,220px)_minmax(0,1fr)_auto]"
            >
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Свойство
                </label>
                <AutocompleteInput
                  v-model="row.field"
                  :options="filterFieldOptions"
                  placeholder="Например, Автор"
                  aria-label="Свойство фильтра"
                  @update:model-value="resetFilterRowValues(row)"
                  @select="resetFilterRowValues(row)"
                />
              </div>

              <div v-if="isRangeFilter(row.field)" class="grid gap-3 sm:grid-cols-2">
                <div>
                  <label class="mb-1 block text-sm font-medium text-slate-700">
                    От
                  </label>
                  <input
                    v-model="row.from"
                    :type="isNumberRangeFilter(row.field) ? 'number' : 'text'"
                    :inputmode="isNumberRangeFilter(row.field) ? 'numeric' : 'text'"
                    placeholder="Начало диапазона"
                    aria-label="Начало диапазона фильтра"
                    class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                  />
                </div>

                <div>
                  <label class="mb-1 block text-sm font-medium text-slate-700">
                    До
                  </label>
                  <input
                    v-model="row.to"
                    :type="isNumberRangeFilter(row.field) ? 'number' : 'text'"
                    :inputmode="isNumberRangeFilter(row.field) ? 'numeric' : 'text'"
                    placeholder="Конец диапазона"
                    aria-label="Конец диапазона фильтра"
                    class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                  />
                </div>
              </div>

              <div v-else>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Значение
                </label>
                <AutocompleteInput
                  v-model="row.value"
                  :options="getFilterValueOptions(row.field)"
                  placeholder="Выберите или введите значение"
                  aria-label="Значение фильтра"
                />
              </div>

              <div class="flex items-end">
                <button
                  @click="removeFilterRow(row.id)"
                  class="w-full rounded-xl border border-slate-300 px-4 py-2 font-medium text-slate-700 hover:bg-slate-100 md:w-auto"
                >
                  Удалить
                </button>
              </div>
            </div>
          </div>

          <div class="mt-4">
            <button
              @click="addFilterRow"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Добавить фильтр
            </button>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            @click="applyFilters"
            class="rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700">
            Найти
          </button>

          <button
            @click="resetFilters"
            class="rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100">
            Сбросить
          </button>
        </div>
      </section>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <section class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div>
            <p class="text-sm text-slate-600">
              Найдено: {{ totalCount }}
            </p>
            <p v-if="isAuthenticated && selectedWorksCount" class="mt-1 text-sm font-medium text-slate-900">
              Выбрано: {{ selectedWorksCount }}
            </p>
          </div>

          <p v-if="loading" class="text-sm text-slate-500">
            Обновление...
          </p>
          
          <div v-if="isAuthenticated" class="flex flex-wrap gap-3">
            <button
              @click="analyzeSelectedWorks"
              :disabled="selectedWorksCount === 0 || analyzing"
              class="rounded-xl bg-slate-900 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {{ analyzing ? "Анализирую..." : "Анализировать выбранные" }}
            </button>
          </div>
        </div>

        <WorksTable
          :works="works"
          :loading="loading"
          :selected-ids="selectedWorkIds"
          :all-filtered-selected="allFilteredSelected"
          :selectable="isAuthenticated"
          @toggle-work="toggleWorkSelection"
          @toggle-all-filtered="toggleAllFilteredWorks"
        />

        <PaginationControls
          :current-page="currentPage"
          :total-pages="totalPages"
          :has-previous="Boolean(previousPageUrl)"
          :has-next="Boolean(nextPageUrl)"
          :loading="loading"
          @previous="goToPreviousPage"
          @next="goToNextPage"
          @page="goToPage"
        />
      </section>
    </div>
  </main>
</template>
