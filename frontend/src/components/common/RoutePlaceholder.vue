<script setup>
defineProps({
  description: {
    type: String,
    required: true,
  },
  emptyText: {
    type: String,
    required: true,
  },
  kicker: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <section class="route-placeholder">
    <div>
      <p class="route-placeholder__kicker">{{ kicker }}</p>
      <h2>{{ title }}</h2>
      <p class="route-placeholder__description">
        {{ description }}
      </p>
    </div>

    <div class="route-placeholder__panel">
      <el-empty :description="emptyText" />
    </div>
  </section>
</template>
