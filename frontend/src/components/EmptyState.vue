<template>
  <div class="flex flex-col items-center justify-center py-16 gap-3 text-center">
    <span class="text-4xl">{{ icon }}</span>
    <p class="text-gray-500 font-medium">{{ title }}</p>
    <p v-if="subtitle" class="text-sm text-gray-400 max-w-xs">{{ subtitle }}</p>
  </div>
</template>

<script setup>
defineProps({
  icon:     { type: String, default: '📭' },
  title:    { type: String, default: 'Nenhum dado disponível' },
  subtitle: { type: String, default: '' },
})
</script>
