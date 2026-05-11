<script setup>
import { computed, ref } from "vue"

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  options: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: "",
  },
  ariaLabel: {
    type: String,
    default: "",
  },
})

const emit = defineEmits(["update:modelValue", "select"])

const isOpen = ref(false)

const filteredOptions = computed(() => {
  const query = props.modelValue.trim().toLowerCase()
  const options = props.options.map((option) => {
    if (typeof option === "string") {
      return {
        label: option,
        value: option,
      }
    }

    return option
  })

  if (!query) return options.slice(0, 50)

  return options
    .filter((option) => {
      return (
        String(option.label).toLowerCase().includes(query) ||
        String(option.value).toLowerCase().includes(query)
      )
    })
    .slice(0, 50)
})

function updateValue(event) {
  emit("update:modelValue", event.target.value)
  isOpen.value = true
}

function selectOption(option) {
  emit("update:modelValue", String(option.label))
  emit("select", option)
  isOpen.value = false
}
</script>

<template>
  <div class="relative">
    <input
      :value="modelValue"
      type="text"
      :placeholder="placeholder"
      :aria-label="ariaLabel"
      autocomplete="off"
      class="w-full rounded-xl border border-slate-300 px-4 py-2 text-slate-900 outline-none focus:border-slate-500"
      @input="updateValue"
      @focus="isOpen = true"
      @blur="isOpen = false"
    />

    <div
      v-if="isOpen && filteredOptions.length"
      class="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-slate-200 bg-white py-1 shadow-lg"
    >
      <button
        v-for="option in filteredOptions"
        :key="option.value"
        type="button"
        class="block w-full px-4 py-2 text-left text-sm text-slate-900 hover:bg-slate-100"
        @mousedown.prevent="selectOption(option)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>
