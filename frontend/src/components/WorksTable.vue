<script setup>
import { computed } from "vue"
import { RouterLink } from "vue-router"

const props = defineProps({
  works: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  selectedIds: {
    type: Set,
    required: true,
  },
  allFilteredSelected: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(["toggle-work", "toggle-all-filtered"])

const pageWorkIds = computed(() => props.works.map((work) => work.id))

const selectedOnPageCount = computed(() => {
  if (props.allFilteredSelected) return props.works.length

  return pageWorkIds.value.filter((id) => props.selectedIds.has(id)).length
})

function isWorkSelected(workId) {
  return props.allFilteredSelected || props.selectedIds.has(workId)
}

function formatWorkDate(work) {
  const dateFrom = String(work.date_from || "").trim()
  const dateTo = String(work.date_to || "").trim()

  if (dateFrom && dateTo && dateFrom !== dateTo) {
    return `${dateFrom}-${dateTo}`
  }

  return dateFrom || dateTo || work.date || ""
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="min-w-[980px] table-fixed border-collapse text-left">
      <colgroup>
        <col class="w-12" />
        <col />
        <col class="w-40" />
        <col class="w-44" />
        <col class="w-44" />
        <col class="w-24" />
      </colgroup>

      <thead class="bg-slate-100 text-sm text-slate-700">
        <tr>
          <th class="px-5 py-3">
            <input
              type="checkbox"
              :checked="allFilteredSelected"
              :indeterminate="!allFilteredSelected && selectedOnPageCount > 0"
              :disabled="works.length === 0"
              class="h-4 w-4 rounded border-slate-300 text-slate-900 accent-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Выбрать все найденные работы"
              @change="emit('toggle-all-filtered')"
            />
          </th>
          <th class="w-[35%] px-5 py-3 font-semibold">Название</th>
          <th class="w-[15%] px-5 py-3 font-semibold">Автор</th>
          <th class="w-[20%] px-5 py-3 font-semibold">Жанр</th>
          <th class="w-[5%] px-5 py-3 font-semibold">Номер</th>
          <th class="w-[25%] px-5 py-3 font-semibold">Дата</th>
        </tr>
      </thead>

      <tbody class="divide-y divide-slate-200">
        <tr
          v-for="work in works"
          :key="work.id"
          class="hover:bg-slate-50"
        >
          <td class="px-5 py-3 align-top">
            <input
              type="checkbox"
              :checked="isWorkSelected(work.id)"
              :disabled="allFilteredSelected"
              class="h-4 w-4 rounded border-slate-300 text-slate-900 accent-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
              :aria-label="`Выбрать работу ${work.title || work.id}`"
              @change="emit('toggle-work', work.id)"
            />
          </td>

          <td class="px-5 py-3">
            <RouterLink
              :to="{ name: 'work-detail', params: { id: work.id } }"
              class="break-words font-medium text-slate-900 hover:text-slate-600 hover:underline">
              {{ work.title || "Без названия" }}
            </RouterLink>
          </td>

          <td class="break-words px-5 py-3 text-sm text-slate-700">
            {{ work.author || "—" }}
          </td>

          <td class="break-words px-5 py-3 text-sm text-slate-700">
            {{ work.genre || "—" }}
          </td>

          <td class="px-5 py-3 text-sm text-slate-700">
            {{ work.number || "—" }}
          </td>

          <td class="px-5 py-3 text-sm text-slate-700">
            <span v-if="formatWorkDate(work)" class="break-words">
              {{ formatWorkDate(work) }}
            </span>
            <span v-else>—</span>
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
</template>
