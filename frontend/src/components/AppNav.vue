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
          class="rounded-lg bg-slate-900 px-3 py-2 font-medium text-white"
        >
          Произведения
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
