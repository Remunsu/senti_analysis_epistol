<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { API_BASE_URL, readApiResponse } from "../api"
import { authFetch, fetchAuthStatus, isAuthenticated } from "../auth"

const route = useRoute()

const work = ref(null)
const loading = ref(false)
const saving = ref(false)
const error = ref("")
const success = ref("")
const selectedSource = ref("xml")
const isEditing = ref(false)
const splitContainer = ref(null)
const textPanelPercent = ref(56)
const isResizing = ref(false)
const workForm = ref(createEmptyWorkForm())

const workId = computed(() => route.params.id)
const pdfPages = computed(() => parsePages(work.value?.pages || ""))
const firstPdfPage = computed(() => pdfPages.value[0] || null)
const firstCorrectedPdfPage = computed(() => {
  if (!firstPdfPage.value) return null

  return getCorrectedPdfPage(firstPdfPage.value)
})
const pdfExtraPages = computed(() => parsePages(work.value?.volume_pdf_extra_pages || ""))
const canPreviewPdf = computed(() => {
  return work.value?.pdf_fragment_url || (work.value?.volume_pdf_url && work.value?.volume_pdf_kind === "pdf")
})
const pdfPreviewUrl = computed(() => work.value?.pdf_fragment_url || "")
const splitStyle = computed(() => ({
  "--left-pane-width": `${textPanelPercent.value}%`,
}))
const visibleSourceTabs = computed(() => {
  const tabs = [{ key: "xml", label: "XML" }]

  if (canPreviewPdf.value) {
    tabs.push({ key: "pdf", label: "PDF" })
  }

  return tabs
})

const workFieldGroups = [
  [
    { key: "source_id", label: "ID источника" },
    { key: "number", label: "Номер", type: "number" },
    { key: "title", label: "Название" },
    { key: "title_short", label: "Краткое название" },
    { key: "title_desc", label: "Описание" },
    { key: "author", label: "Автор" },
    { key: "recipient", label: "Адресат" },
  ],
  [
    { key: "genre", label: "Жанр" },
    { key: "language", label: "Язык" },
    { key: "date_from", label: "Дата от" },
    { key: "date_to", label: "Дата до" },
    { key: "place", label: "Место" },
    { key: "pages", label: "Страницы" },
    { key: "note", label: "Примечание" },
  ],
]

function createEmptyWorkForm() {
  return {
    source_id: "",
    note: "",
    number: "",
    date_from: "",
    date_to: "",
    place: "",
    pages: "",
    author: "",
    recipient: "",
    language: "",
    title_desc: "",
    title_short: "",
    title: "",
    genre: "",
    plain_text: "",
    raw_xml: "",
  }
}

const properties = computed(() => {
  if (!work.value) return []

  return [
    { label: "ID источника", value: work.value.source_id },
    {
      label: "Том",
      value: work.value.volume_title || work.value.volume,
      to: work.value.volume
        ? { name: "volume-detail", params: { id: work.value.volume } }
        : null,
    },
    { label: "Номер", value: work.value.number },
    { label: "Название", value: work.value.title },
    { label: "Краткое название", value: work.value.title_short },
    { label: "Описание", value: work.value.title_desc },
    { label: "Автор", value: work.value.author },
    { label: "Адресат", value: work.value.recipient },
    { label: "Жанр", value: work.value.genre },
    { label: "Дата", value: formatWorkDate(work.value) },
    { label: "Страницы", value: work.value.pages },
    { label: "Место", value: work.value.place },
    { label: "Язык", value: work.value.language },
    { label: "Примечание", value: work.value.note },
    { label: "Создано", value: formatDateTime(work.value.created_at) },
  ].filter((property) => hasPropertyValue(property.value))
})

function hasPropertyValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== ""
}

function formatWorkDate(workData) {
  const dateFrom = String(workData.date_from || "").trim()
  const dateTo = String(workData.date_to || "").trim()

  if (dateFrom && dateTo && dateFrom !== dateTo) {
    return `${dateFrom}-${dateTo}`
  }

  return dateFrom || dateTo || workData.date || ""
}

function formatDateTime(value) {
  if (!value) return ""

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

function parsePages(value) {
  const pages = []
  const seen = new Set()
  const parts = String(value || "").split(/[,\s;]+/).filter(Boolean)

  parts.forEach((part) => {
    const rangeMatch = part.match(/^(\d+)[-–—](\d+)$/)

    if (rangeMatch) {
      const start = Number(rangeMatch[1])
      const end = Number(rangeMatch[2])
      const min = Math.min(start, end)
      const max = Math.max(start, end)

      for (let page = min; page <= max; page += 1) {
        addPage(page, pages, seen)
      }

      return
    }

    const page = Number(part)

    if (Number.isInteger(page)) {
      addPage(page, pages, seen)
    }
  })

  return pages.slice(0, 20)
}

function addPage(page, pages, seen) {
  if (page < 1 || seen.has(page)) return

  seen.add(page)
  pages.push(page)
}

function pdfPageUrl(page) {
  return `${work.value.volume_pdf_url}#page=${page}&view=FitH`
}

function getCorrectedPdfPage(page) {
  const offset = Number(work.value?.volume_pdf_page_offset || 0)
  const extraPages = pdfExtraPages.value
  let correctedPage = Math.max(1, page + offset)
  let previousPage = 0
  let attempts = 0

  while (correctedPage !== previousPage && attempts < extraPages.length + 2) {
    previousPage = correctedPage
    correctedPage = Math.max(
      1,
      page + offset + extraPages.filter((extraPage) => extraPage <= previousPage).length,
    )
    attempts += 1
  }

  return correctedPage
}

function selectSource(source) {
  if (source === "pdf" && !canPreviewPdf.value) return

  selectedSource.value = source
}

function startResizing(event) {
  if (!splitContainer.value) return

  isResizing.value = true
  updatePanelWidth(event)
  window.addEventListener("pointermove", updatePanelWidth)
  window.addEventListener("pointerup", stopResizing)
}

function updatePanelWidth(event) {
  const container = splitContainer.value

  if (!container) return

  const rect = container.getBoundingClientRect()
  const percent = ((event.clientX - rect.left) / rect.width) * 100

  textPanelPercent.value = Math.min(80, Math.max(45, Math.round(percent)))
}

function stopResizing() {
  isResizing.value = false
  window.removeEventListener("pointermove", updatePanelWidth)
  window.removeEventListener("pointerup", stopResizing)
}

function fillWorkForm() {
  if (!work.value) return

  workForm.value = {
    source_id: work.value.source_id || "",
    note: work.value.note || "",
    number: work.value.number ?? "",
    date_from: work.value.date_from || "",
    date_to: work.value.date_to || "",
    place: work.value.place || "",
    pages: work.value.pages || "",
    author: work.value.author || "",
    recipient: work.value.recipient || "",
    language: work.value.language || "",
    title_desc: work.value.title_desc || "",
    title_short: work.value.title_short || "",
    title: work.value.title || "",
    genre: work.value.genre || "",
    plain_text: work.value.plain_text || "",
    raw_xml: work.value.raw_xml || "",
  }
}

function startEditing() {
  fillWorkForm()
  error.value = ""
  success.value = ""
  isEditing.value = true
}

function cancelEditing() {
  fillWorkForm()
  isEditing.value = false
}

function buildWorkPayload() {
  return {
    ...workForm.value,
    number: workForm.value.number === "" ? null : Number(workForm.value.number),
  }
}

async function saveWork() {
  if (!work.value || saving.value) return

  saving.value = true
  error.value = ""
  success.value = ""

  try {
    const response = await authFetch(`${API_BASE_URL}/works/${workId.value}/`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(buildWorkPayload()),
    })
    const data = await readApiResponse(response, "Не удалось сохранить документ")

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось сохранить документ")
    }

    work.value = data
    fillWorkForm()
    isEditing.value = false
    success.value = "Документ сохранен"
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    saving.value = false
  }
}

async function fetchWork() {
  loading.value = true
  error.value = ""
  success.value = ""
  isEditing.value = false

  try {
    const response = await fetch(`${API_BASE_URL}/works/${workId.value}/`)

    if (!response.ok) {
      throw new Error("Не удалось загрузить документ")
    }

    work.value = await response.json()
    fillWorkForm()
  } catch (err) {
    error.value = err.message || "Неизвестная ошибка"
  } finally {
    loading.value = false
  }
}

watch(workId, () => {
  fetchWork()
})

watch(canPreviewPdf, (canPreview) => {
  if (!canPreview && selectedSource.value === "pdf") {
    selectedSource.value = "xml"
  }
})

onMounted(() => {
  fetchAuthStatus().catch(() => {})
  fetchWork()
})

onBeforeUnmount(() => {
  stopResizing()
})
</script>

<template>
  <main class="p-6">
    <div class="mx-auto max-w-7xl">
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="mt-3 text-3xl font-bold text-slate-900">
            {{ work?.title || "Документ" }}
          </h1>
        </div>

        <div v-if="work && isAuthenticated" class="flex flex-wrap gap-3">
          <button
            v-if="!isEditing"
            type="button"
            @click="startEditing"
            class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Редактировать
          </button>

          <template v-else>
            <button
              type="button"
              @click="saveWork"
              :disabled="saving"
              class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {{ saving ? "Сохраняю..." : "Сохранить" }}
            </button>

            <button
              type="button"
              @click="cancelEditing"
              :disabled="saving"
              class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Отменить
            </button>
          </template>

        </div>
      </div>

      <div v-if="error" class="mb-4 rounded-xl bg-red-50 p-4 text-red-700">
        {{ error }}
      </div>

      <div v-if="success" class="mb-4 rounded-xl bg-emerald-50 p-4 text-emerald-700">
        {{ success }}
      </div>

      <div v-if="loading" class="rounded-2xl bg-white p-5 text-slate-500 shadow-sm ring-1 ring-slate-200">
        Загрузка документа...
      </div>

      <template v-else-if="work">
        <section class="mb-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          <form v-if="isEditing" class="space-y-6" @submit.prevent="saveWork">
            <div
              v-for="(group, groupIndex) in workFieldGroups"
              :key="groupIndex"
              class="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
            >
              <div
                v-for="field in group"
                :key="field.key"
              >
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  {{ field.label }}
                </label>
                <input
                  v-model="workForm[field.key]"
                  :type="field.type || 'text'"
                  class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
                />
              </div>
            </div>

            <div class="grid gap-4 xl:grid-cols-2">
              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  Текст
                </label>
                <textarea
                  v-model="workForm.plain_text"
                  class="min-h-[28rem] w-full resize-none rounded-xl border border-slate-300 p-4 font-mono text-sm leading-6 text-slate-900 outline-none focus:border-slate-500"
                />
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-slate-700">
                  XML
                </label>
                <textarea
                  v-model="workForm.raw_xml"
                  class="min-h-[28rem] w-full resize-none rounded-xl border border-slate-300 p-4 font-mono text-sm leading-6 text-slate-900 outline-none focus:border-slate-500"
                />
              </div>
            </div>
          </form>

          <dl v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <div
              v-for="property in properties"
              :key="property.label"
              class="min-w-0 border-b border-slate-100 pb-3"
            >
              <dt class="text-xs font-semibold uppercase text-slate-500">
                {{ property.label }}
              </dt>
              <dd class="mt-1 break-words text-sm text-slate-900">
                <RouterLink
                  v-if="property.to"
                  :to="property.to"
                  class="font-medium text-slate-900 hover:text-slate-600 hover:underline"
                >
                  {{ property.value }}
                </RouterLink>
                <template v-else>
                  {{ property.value }}
                </template>
              </dd>
            </div>
          </dl>
        </section>

        <section v-if="!isEditing" class="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">
                Содержимое
              </h2>
              <p
                v-if="selectedSource === 'pdf' && work.pages"
                class="mt-1 text-sm text-slate-600"
              >
                Страницы: {{ work.pages }}
                <span v-if="firstCorrectedPdfPage && firstCorrectedPdfPage !== firstPdfPage">
                  · PDF: {{ firstCorrectedPdfPage }}
                </span>
              </p>
            </div>

            <div class="flex flex-wrap items-center gap-3">
              <a
                v-if="selectedSource === 'pdf' && work.volume_pdf_url"
                :href="work.volume_pdf_url"
                target="_blank"
                rel="noreferrer"
                class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                Открыть файл
              </a>

              <div class="flex rounded-xl border border-slate-300 bg-white p-1">
                <button
                  v-for="tab in visibleSourceTabs"
                  :key="tab.key"
                  type="button"
                  @click="selectSource(tab.key)"
                  :class="[
                    'rounded-lg px-4 py-2 text-sm font-medium',
                    selectedSource === tab.key
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-700 hover:bg-slate-100',
                  ]"
                >
                  {{ tab.label }}
                </button>
              </div>
            </div>
          </div>

          <div
            ref="splitContainer"
            class="content-split-grid"
            :style="splitStyle"
          >
            <div class="border-b border-slate-200 xl:border-b-0 xl:border-r">
              <div class="border-b border-slate-200 px-5 py-3">
                <h3 class="text-sm font-semibold text-slate-900">
                  Текст
                </h3>
              </div>
              <textarea
                readonly
                :value="work.plain_text || ''"
                class="min-h-[36rem] w-full resize-none border-0 bg-white p-5 font-mono text-sm leading-6 text-slate-900 outline-none"
              />
            </div>

            <button
              type="button"
              aria-label="Изменить ширину панелей"
              :class="[
                'resize-hitbox hidden cursor-col-resize xl:block',
                isResizing ? 'is-resizing' : '',
              ]"
              @pointerdown.prevent="startResizing"
            />

            <div>
              <div class="border-b border-slate-200 px-5 py-3">
                <h3 class="text-sm font-semibold text-slate-900">
                  {{ selectedSource === "pdf" ? "PDF" : "XML" }}
                </h3>
              </div>

              <template v-if="selectedSource === 'pdf'">
                <div v-if="pdfPages.length === 0" class="p-5">
                  <div class="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
                    У документа не указаны страницы для показа.
                  </div>
                </div>

                <div v-else>
                  <iframe
                    v-if="pdfPreviewUrl"
                    :src="pdfPreviewUrl"
                    :title="`PDF-фрагмент документа ${work.title || work.id}`"
                    class="h-[72vh] min-h-[42rem] w-full border-0 bg-slate-100"
                  />
                  <iframe
                    v-else-if="firstCorrectedPdfPage"
                    :src="pdfPageUrl(firstCorrectedPdfPage)"
                    :title="`Страница ${firstCorrectedPdfPage}`"
                    class="h-[72vh] min-h-[42rem] w-full border-0 bg-slate-100"
                  />
                </div>
              </template>

              <textarea
                v-else
                readonly
                :value="work.raw_xml || ''"
                class="min-h-[36rem] w-full resize-none border-0 bg-white p-5 font-mono text-sm leading-6 text-slate-900 outline-none"
              />
            </div>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>

<style scoped>
.content-split-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}

@media (min-width: 1280px) {
  .content-split-grid {
    position: relative;
    grid-template-columns:
      minmax(0, var(--left-pane-width))
      minmax(0, calc(100% - var(--left-pane-width)));
  }

  .resize-hitbox {
    position: absolute;
    inset-block: 0;
    left: var(--left-pane-width);
    z-index: 10;
    width: 1rem;
    transform: translateX(-50%);
    background: transparent;
  }

  .resize-hitbox.is-resizing {
    background: rgb(15 23 42 / 0.04);
  }
}
</style>
