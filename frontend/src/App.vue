<template>
  <AppLayout>
    <router-view></router-view>
  </AppLayout>
</template>

<script setup>
import AppLayout from "./components/AppLayout.vue";
</script>

<style>
/* Global styles */
body {
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
    Arial, sans-serif;
  margin: 0;
  padding: 0;
}
</style>
