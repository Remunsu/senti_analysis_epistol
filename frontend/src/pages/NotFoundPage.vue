<template>
  <main class="p-6">
    <div class="mx-auto max-w-3xl rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
      <p class="text-sm font-semibold text-slate-500">
        404
      </p>

      <h1 class="mt-2 text-3xl font-bold text-slate-900">
        Страница не найдена
      </h1>

      <p class="mt-3 text-slate-600">
        Такой страницы нет или адрес указан с ошибкой.
      </p>

      <div class="mt-6 flex flex-wrap gap-3">
        <RouterLink
          to="/"
          class="rounded-xl bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-700"
        >
          К произведениям
        </RouterLink>

        <RouterLink
          to="/volumes"
          class="rounded-xl border border-slate-300 px-5 py-2 font-medium text-slate-700 hover:bg-slate-100"
        >
          К томам
        </RouterLink>
      </div>
    </div>
  </main>
</template>
