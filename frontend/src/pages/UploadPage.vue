<script setup>
import { computed, ref } from "vue"
import { RouterLink } from "vue-router"

const selectedMode = ref("volume")
const selectedFile = ref(null)
const submitting = ref(false)
const error = ref("")
const uploadResult = ref(null)

const API_BASE_URL = "http://127.0.0.1:8000/api"

const modeOptions = [
  {
    value: "volume",
    label: "Том",
    description: "XML с набором TEI-произведений внутри тома",
  },
  {
    value: "work",
    label: "Одно произведение",
    description: "XML одного TEI-произведения",
  },
]

const uploadedWorks = computed(() => uploadResult.value?.works || [])

function handleFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null
  uploadResult.value = null
  error.value = ""
}

async function uploadXml() {
  if (!selectedFile.value) {
    error.value = "Выберите XML-файл"
    return
  }

  submitting.value = true
  error.value = ""
  uploadResult.value = null

  const formData = new FormData()

  formData.append("mode", selectedMode.value)
  formData.append("file", selectedFile.value)

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
          <h2 class="mb-3 text-sm font-semibold text-slate-900">
            Тип загрузки
          </h2>

          <div class="grid gap-3 md:grid-cols-2">
            <label
              v-for="option in modeOptions"
              :key="option.value"
              :class="[
                'cursor-pointer rounded-xl border p-4',
                selectedMode === option.value
                  ? 'border-slate-900 bg-slate-50'
                  : 'border-slate-200 hover:bg-slate-50',
              ]"
            >
              <input
                v-model="selectedMode"
                type="radio"
                name="upload-mode"
                :value="option.value"
                class="sr-only"
              />
              <span class="block font-semibold text-slate-900">
                {{ option.label }}
              </span>
              <span class="mt-1 block text-sm text-slate-600">
                {{ option.description }}
              </span>
            </label>
          </div>
        </div>

        <div class="mb-5">
          <label class="mb-2 block text-sm font-semibold text-slate-900">
            XML-файл
          </label>
          <input
            type="file"
            accept=".xml,text/xml,application/xml"
            class="block w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:font-medium file:text-white hover:file:bg-slate-700"
            @change="handleFileChange"
          />
          <p v-if="selectedFile" class="mt-2 text-sm text-slate-600">
            Выбран файл: {{ selectedFile.name }}
          </p>
        </div>

        <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
          {{ error }}
        </div>

        <button
          @click="uploadXml"
          :disabled="submitting || !selectedFile"
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
            :to="{ name: 'volume-detail', params: { id: uploadResult.volume.id } }"
            class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Открыть том
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
            Создано произведений: {{ uploadedWorks.length }}
          </p>

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
