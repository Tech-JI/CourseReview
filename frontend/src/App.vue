<template>
  <div class="app-container">
    <Navbar v-if="showNavbar" />
    
    <main class="main-content">
      <router-view></router-view>
    </main>
    
    <Footer v-if="showFooter" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from './components/Navbar.vue'
import Footer from './components/Footer.vue'

const route = useRoute()

// Don't show navbar/footer on auth pages
const showNavbar = computed(() => {
  return !route.path.startsWith('/accounts')
})

const showFooter = computed(() => {
  return !route.path.startsWith('/accounts')
})
</script>

<style>
/* Global styles */
:root {
  --el-color-primary: #409EFF;
}

html, body {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  padding-top: 80px; /* Offset for fixed navbar */
  padding-bottom: 2rem;
}

a {
  text-decoration: none;
  color: inherit;
}

/* Responsive breakpoints */
@media (max-width: 768px) {
  .main-content {
    padding-top: 60px;
  }
}
</style>
