<template>
  <div class="flex flex-col items-center justify-center py-16 gap-4">
    <div class="spinner w-10 h-10"></div>
    <p class="text-sm text-gray-400">{{ message }}</p>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'Carregando dados...' }
})
</script>
