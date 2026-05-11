<script setup>
import { computed } from "vue"

const props = defineProps({
  currentPage: {
    type: Number,
    required: true,
  },
  totalPages: {
    type: Number,
    required: true,
  },
  hasPrevious: {
    type: Boolean,
    default: false,
  },
  hasNext: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(["previous", "next", "page"])

const visiblePages = computed(() => {
  const pages = new Set([
    1,
    props.totalPages,
    props.currentPage - 1,
    props.currentPage,
    props.currentPage + 1,
  ])

  return [...pages]
    .filter((page) => page >= 1 && page <= props.totalPages)
    .sort((left, right) => left - right)
})

const pageItems = computed(() => {
  const items = []

  visiblePages.value.forEach((page, index) => {
    const previousPage = visiblePages.value[index - 1]

    if (previousPage && page - previousPage > 1) {
      items.push({
        type: "gap",
        key: `gap-${previousPage}-${page}`,
      })
    }

    items.push({
      type: "page",
      key: `page-${page}`,
      page,
    })
  })

  return items
})
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-5 py-4">
    <p class="text-sm text-slate-600">
      Страница {{ currentPage }} из {{ totalPages }}
    </p>

    <div class="flex items-center gap-2">
      <button
        @click="emit('previous')"
        :disabled="!hasPrevious || loading"
        class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Назад
      </button>

      <template
        v-for="item in pageItems"
        :key="item.key"
      >
        <span
          v-if="item.type === 'gap'"
          class="px-2 text-slate-500"
        >
          ...
        </span>

        <button
          v-else-if="item.page === currentPage"
          class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
        >
          {{ item.page }}
        </button>

        <button
          v-else
          @click="emit('page', item.page)"
          :disabled="loading"
          class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {{ item.page }}
        </button>
      </template>

      <button
        @click="emit('next')"
        :disabled="!hasNext || loading"
        class="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Вперёд
      </button>
    </div>
  </div>
</template>
