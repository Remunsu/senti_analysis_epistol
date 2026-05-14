<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { API_BASE_URL } from "../api"
import PaginationControls from "../components/PaginationControls.vue"

const route = useRoute()

const volume = ref(null)
const works = ref([])
const loading = ref(false)
const worksLoading = ref(false)
const facsimileUploading = ref(false)
const error = ref("")
const facsimileInput = ref(null)

const currentPage = ref(1)
const totalCount = ref(0)
const nextPageUrl = ref(null)
const previousPageUrl = ref(null)

const pageSize = 50

const volumeId = computed(() => route.params.id)

const totalPages = computed(() => {
  if (!totalCount.value) return 1

  return Math.ceil(totalCount.value / pageSize)
})

const properties = computed(() => {
  if (!volume.value) return []

  return [
    ["ID источника", volume.value.source_id],
    ["Номер", volume.value.number],
    ["Название", volume.value.title],
    ["Краткое название", volume.value.title_short],
    ["Автор", volume.value.author],
    ["Факсимиле", volume.value.facsimile_name],
    ["Загружен", formatDateTime(volume.value.uploaded_at)],
  ]
})

function formatDateTime(value) {
  if (!value) return ""

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

async function fetchVolume() {
  loading.value = true
  error.value = ""

  try {
    const response = await fetch(`${API_BASE_URL}/volumes/${volumeId.value}/`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить том")
    }

    volume.value = await response.json()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

async function fetchWorks(page = 1) {
  worksLoading.value = true
  error.value = ""

  const params = new URLSearchParams()

  params.append("volume", volumeId.value)
  params.append("page", page)
  params.append("ordering", "number")

  try {
    const response = await fetch(`${API_BASE_URL}/works/?${params.toString()}`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить произведения тома")
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
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    worksLoading.value = false
  }
}

function openFacsimilePicker() {
  facsimileInput.value?.click()
}

async function uploadFacsimile(event) {
  const file = event.target.files?.[0]

  event.target.value = ""

  if (!file || facsimileUploading.value) return

  if (!isAllowedFacsimileFile(file)) {
    error.value = "Можно загрузить только PDF, DJVU или DJV"
    return
  }

  facsimileUploading.value = true
  error.value = ""

  const formData = new FormData()

  formData.append("file", file)

  try {
    const response = await fetch(`${API_BASE_URL}/volumes/${volumeId.value}/facsimile/`, {
      method: "POST",
      body: formData,
    })
    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить файл тома")
    }

    volume.value = data
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    facsimileUploading.value = false
  }
}

function isAllowedFacsimileFile(file) {
  const name = file.name.toLowerCase()

  return name.endsWith(".pdf") || name.endsWith(".djvu") || name.endsWith(".djv")
}

function goToPage(page) {
  if (page < 1 || page > totalPages.value || worksLoading.value) return

  fetchWorks(page)
}

function goToPreviousPage() {
  if (!previousPageUrl.value || worksLoading.value) return

  fetchWorks(currentPage.value - 1)
}

function goToNextPage() {
  if (!nextPageUrl.value || worksLoading.value) return

  fetchWorks(currentPage.value + 1)
}

async function fetchPageData() {
  await Promise.all([
    fetchVolume(),
    fetchWorks(1),
  ])
}

watch(volumeId, () => {
  currentPage.value = 1
  fetchPageData()
})

onMounted(() => {
  fetchPageData()
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-900">
          {{ volume?.title || "Том" }}
        </h1>
      </div>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div v-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загрузка тома...
      </div>

      <template v-else-if="volume">
        <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 class="text-lg font-semibold text-slate-900">
              Свойства
            </h2>

            <div class="flex flex-wrap items-center gap-3">
              <a
                v-if="volume.facsimile_url"
                :href="volume.facsimile_url"
                target="_blank"
                rel="noreferrer"
                class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                Открыть файл
              </a>

              <button
                type="button"
                @click="openFacsimilePicker"
                :disabled="facsimileUploading"
                class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {{ facsimileUploading ? "Загружаю..." : "Загрузить PDF/DJVU" }}
              </button>

              <input
                ref="facsimileInput"
                type="file"
                accept=".pdf,.djvu,.djv,application/pdf,image/vnd.djvu"
                class="hidden"
                @change="uploadFacsimile"
              />
            </div>
          </div>

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
                {{ value || "—" }}
              </dd>
            </div>
          </dl>
        </section>

        <section class="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">
                Произведения
              </h2>
              <p class="mt-1 text-sm text-slate-600">
                Найдено: {{ totalCount }}
              </p>
            </div>

            <p v-if="worksLoading" class="text-sm text-slate-500">
              Обновление таблицы...
            </p>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full border-collapse text-left">
              <thead class="bg-slate-100 text-sm text-slate-700">
                <tr>
                  <th class="w-[45%] px-5 py-3 font-semibold">Название</th>
                  <th class="w-[15%] px-5 py-3 font-semibold">Автор</th>
                  <th class="w-[20%] px-5 py-3 font-semibold">Жанр</th>
                  <th class="w-[10%] px-5 py-3 font-semibold">Дата</th>
                  <th class="w-[10%] px-5 py-3 font-semibold">Номер</th>
                </tr>
              </thead>

              <tbody class="divide-y divide-slate-200">
                <tr
                  v-for="work in works"
                  :key="work.id"
                  class="hover:bg-slate-50"
                >
                  <td class="max-w-md px-5 py-3">
                    <RouterLink
                      :to="{ name: 'work-detail', params: { id: work.id } }"
                      class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
                    >
                      {{ work.title || "Без названия" }}
                    </RouterLink>
                    <div v-if="work.title_short" class="mt-1 text-sm text-slate-500">
                      {{ work.title_short }}
                    </div>
                  </td>

                  <td class="px-5 py-3 text-sm text-slate-700">
                    {{ work.author || "—" }}
                  </td>

                  <td class="px-5 py-3 text-sm text-slate-700">
                    {{ work.genre || "—" }}
                  </td>

                  <td class="px-5 py-3 text-slate-700">
                    {{ work.date || "—" }}
                  </td>

                  <td class="px-5 py-3 text-slate-700">
                    {{ work.number || "—" }}
                  </td>
                </tr>

                <tr v-if="!worksLoading && works.length === 0">
                  <td colspan="5" class="px-5 py-8 text-center text-slate-500">
                    Произведения не найдены
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <PaginationControls
            :current-page="currentPage"
            :total-pages="totalPages"
            :has-previous="Boolean(previousPageUrl)"
            :has-next="Boolean(nextPageUrl)"
            :loading="worksLoading"
            @previous="goToPreviousPage"
            @next="goToNextPage"
            @page="goToPage"
          />
        </section>
      </template>
    </div>
  </main>
</template>
