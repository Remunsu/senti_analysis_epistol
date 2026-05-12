<script setup>
import { computed, ref } from "vue"
import { RouterLink } from "vue-router"

const selectedFiles = ref([])
const submitting = ref(false)
const error = ref("")
const uploadResult = ref(null)

const API_BASE_URL = "http://127.0.0.1:8000/api"

const uploadedWorks = computed(() => uploadResult.value?.works || [])
const uploadedVolumes = computed(() => uploadResult.value?.volumes || [])
const selectedFilesCount = computed(() => selectedFiles.value.length)

function isXmlFile(file) {
  return (
    file.name.toLowerCase().endsWith(".xml") ||
    ["text/xml", "application/xml"].includes(file.type)
  )
}

function handleFileChange(event) {
  const files = Array.from(event.target.files || [])
  const invalidFiles = files.filter((file) => !isXmlFile(file))

  uploadResult.value = null

  if (invalidFiles.length) {
    selectedFiles.value = []
    error.value = `Можно загружать только XML-файлы: ${invalidFiles.map((file) => file.name).join(", ")}`
    return
  }

  selectedFiles.value = files
  error.value = ""
}

async function uploadXml() {
  if (!selectedFiles.value.length) {
    error.value = "Выберите один или несколько XML-файлов"
    return
  }

  submitting.value = true
  error.value = ""
  uploadResult.value = null

  const formData = new FormData()

  formData.append("mode", "volume")
  selectedFiles.value.forEach((file) => {
    formData.append("files", file)
  })

  try {
    const response = await fetch(`${API_BASE_URL}/upload/`, {
      method: "POST",
      body: formData,
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось загрузить XML")
    }

    uploadResult.value = data
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-4xl">
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-900">
          Загрузка XML
        </h1>
      </div>

      <section class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <div class="mb-5">
          <label class="mb-2 block text-sm font-semibold text-slate-900">
            XML-файлы томов
          </label>
          <input
            type="file"
            multiple
            accept=".xml,text/xml,application/xml"
            class="block w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:font-medium file:text-white hover:file:bg-slate-700"
            @change="handleFileChange"
          />
          <div v-if="selectedFiles.length" class="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <p class="text-sm font-medium text-slate-900">
              Выбрано файлов: {{ selectedFilesCount }}
            </p>

            <ul class="mt-2 space-y-1 text-sm text-slate-600">
              <li
                v-for="file in selectedFiles"
                :key="`${file.name}-${file.size}`"
              >
                {{ file.name }}
              </li>
            </ul>
          </div>
        </div>

        <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
          {{ error }}
        </div>

        <button
          @click="uploadXml"
          :disabled="submitting || !selectedFiles.length"
          class="rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {{ submitting ? "Загрузка..." : "Загрузить" }}
        </button>
      </section>

      <section
        v-if="uploadResult"
        class="mt-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200"
      >
        <h2 class="text-lg font-semibold text-slate-900">
          XML загружен
        </h2>

        <div class="mt-4 flex flex-wrap gap-3">
          <RouterLink
            v-if="uploadedVolumes.length === 1"
            :to="{ name: 'volume-detail', params: { id: uploadedVolumes[0].id } }"
            class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Открыть том
          </RouterLink>

          <RouterLink
            v-else
            to="/volumes"
            class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Открыть список томов
          </RouterLink>

          <RouterLink
            v-if="uploadedWorks.length === 1"
            :to="{ name: 'work-detail', params: { id: uploadedWorks[0].id } }"
            class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Открыть произведение
          </RouterLink>
        </div>

        <div class="mt-5">
          <p class="text-sm text-slate-600">
            Создано томов: {{ uploadedVolumes.length }}
          </p>
          <p class="text-sm text-slate-600">
            Создано произведений: {{ uploadedWorks.length }}
          </p>

          <ul v-if="uploadedVolumes.length > 1" class="mt-3 divide-y divide-slate-200 rounded-xl border border-slate-200">
            <li
              v-for="volume in uploadedVolumes"
              :key="volume.id"
              class="px-4 py-3"
            >
              <RouterLink
                :to="{ name: 'volume-detail', params: { id: volume.id } }"
                class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
              >
                {{ volume.title || "Без названия" }}
              </RouterLink>
              <p class="mt-1 text-sm text-slate-500">
                {{ volume.author || "Автор не указан" }}
              </p>
            </li>
          </ul>

          <ul v-if="uploadedWorks.length" class="mt-3 divide-y divide-slate-200 rounded-xl border border-slate-200">
            <li
              v-for="work in uploadedWorks"
              :key="work.id"
              class="px-4 py-3"
            >
              <RouterLink
                :to="{ name: 'work-detail', params: { id: work.id } }"
                class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
              >
                {{ work.title || "Без названия" }}
              </RouterLink>
              <p class="mt-1 text-sm text-slate-500">
                {{ work.author || "Автор не указан" }} · {{ work.genre || "Жанр не указан" }}
              </p>
            </li>
          </ul>
        </div>
      </section>
    </div>
  </main>
</template>
