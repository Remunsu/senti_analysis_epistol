<script setup>
import { RouterLink } from "vue-router"
</script>

<template>
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
      <div class="text-base font-semibold text-slate-900">
        Sentiment Analysis
      </div>

      <nav class="flex items-center gap-2 text-sm">
        <RouterLink
          to="/"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Произведения
        </RouterLink>
        <RouterLink
          to="/volumes"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Тома
        </RouterLink>
        <RouterLink
          to="/upload"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Загрузка XML
        </RouterLink>
        <RouterLink
          to="/annotation"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Разметка
        </RouterLink>
        <RouterLink
          to="/sentiment/results"
          class="rounded-lg px-3 py-2 font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          active-class="bg-slate-900 text-white hover:bg-slate-900 hover:text-white"
        >
          Результаты
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
