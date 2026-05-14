<script setup>
import { computed, onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import { API_BASE_URL } from "../api"
import PaginationControls from "../components/PaginationControls.vue"

const volumes = ref([])
const loading = ref(false)
const error = ref("")

const currentPage = ref(1)
const totalCount = ref(0)
const nextPageUrl = ref(null)
const previousPageUrl = ref(null)

const pageSize = 50

const totalPages = computed(() => {
  if (!totalCount.value) return 1

  return Math.ceil(totalCount.value / pageSize)
})

function formatDateTime(value) {
  if (!value) return ""

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

async function fetchVolumes(page = 1) {
  loading.value = true
  error.value = ""

  const params = new URLSearchParams()

  params.append("page", page)

  try {
    const response = await fetch(`${API_BASE_URL}/volumes/?${params.toString()}`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить тома")
    }

    const data = await response.json()

    if (Array.isArray(data)) {
      volumes.value = data
      totalCount.value = data.length
      nextPageUrl.value = null
      previousPageUrl.value = null
      currentPage.value = 1
    } else {
      volumes.value = data.results
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

function goToPage(page) {
  if (page < 1 || page > totalPages.value || loading.value) return

  fetchVolumes(page)
}

function goToPreviousPage() {
  if (!previousPageUrl.value || loading.value) return

  fetchVolumes(currentPage.value - 1)
}

function goToNextPage() {
  if (!nextPageUrl.value || loading.value) return

  fetchVolumes(currentPage.value + 1)
}

onMounted(() => {
  fetchVolumes(1)
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-900">
          Тома
        </h1>
      </div>

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
                <th class="w-[18%] px-5 py-3 font-semibold">Автор</th>
                <th class="w-[15%] px-5 py-3 font-semibold">ID источника</th>
                <th class="w-[12%] px-5 py-3 font-semibold">Работ</th>
                <th class="w-[15%] px-5 py-3 font-semibold">Загружен</th>
              </tr>
            </thead>

            <tbody class="divide-y divide-slate-200">
              <tr
                v-for="volume in volumes"
                :key="volume.id"
                class="hover:bg-slate-50"
              >

                <td class="max-w-md px-5 py-3">
                  <RouterLink
                    :to="{ name: 'volume-detail', params: { id: volume.id } }"
                    class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
                  >
                    {{ volume.title || "Без названия" }}
                  </RouterLink>
                  <div v-if="volume.title_short" class="mt-1 text-sm text-slate-500">
                    {{ volume.title_short }}
                  </div>
                </td>

                <td class="px-5 py-3 text-sm text-slate-700">
                  {{ volume.author || "—" }}
                </td>

                <td class="px-5 py-3 text-sm text-slate-700">
                  {{ volume.source_id || "—" }}
                </td>

                <td class="px-5 py-3 text-sm text-slate-700">
                  {{ volume.works_count ?? 0 }}
                </td>

                <td class="px-5 py-3 text-sm text-slate-700">
                  {{ formatDateTime(volume.uploaded_at) || "—" }}
                </td>
              </tr>

              <tr v-if="!loading && volumes.length === 0">
                <td colspan="5" class="px-5 py-8 text-center text-slate-500">
                  Тома не найдены
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
          :loading="loading"
          @previous="goToPreviousPage"
          @next="goToNextPage"
          @page="goToPage"
        />
      </section>
    </div>
  </main>
</template>
