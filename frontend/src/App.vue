<template>
  <v-app>
    <v-app-bar color="primary" density="compact" elevation="2">
      <v-app-bar-title>
        <router-link to="/" class="text-decoration-none text-white">JI Course Review</router-link>
      </v-app-bar-title>
      <v-spacer></v-spacer>
      <v-btn to="/best" variant="text" class="text-white">Best Courses</v-btn>
      <v-btn to="/layups" variant="text" class="text-white">Layups</v-btn>
      <v-btn to="/departments" variant="text" class="text-white">Departments</v-btn>
      <v-spacer></v-spacer>
      <v-responsive max-width="400" class="mx-4" v-if="showSearchBar">
        <v-form @submit.prevent="performSearch">
          <v-text-field v-model="searchQuery" density="compact" variant="solo" hide-details
            placeholder="Search courses (e.g., ENGR101)" append-inner-icon="mdi-magnify"
            @click:append-inner="performSearch" bg-color="white"></v-text-field>
        </v-form>
      </v-responsive>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view></router-view>
      </v-container>
    </v-main>

    <v-footer app class="bg-primary text-center d-flex flex-column">
      <div>
        <v-btn v-for="icon in icons" :key="icon" class="mx-2" :icon="icon" variant="text" color="white"
          size="small"></v-btn>
      </div>
      <div class="text-white text-caption mt-2">
        &copy; {{ new Date().getFullYear() }} — JI Course Review
      </div>
    </v-footer>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const searchQuery = ref('');
const icons = ['mdi-github', 'mdi-linkedin', 'mdi-twitter'];

// Determine if we should show the search bar
const showSearchBar = computed(() => {
  // Don't show search bar on the landing page or search page
  return route.path !== '/' && route.path !== '/search';
});

onMounted(() => {
  // Initialize search query from route if we're on the search page
  if (route.path === '/search' && route.query.q) {
    searchQuery.value = route.query.q;
  }
});

const performSearch = () => {
  const query = searchQuery.value.trim();
  if (query.length >= 2) {
    router.push({
      path: '/search',
      query: { q: query }
    });
  } else {
    alert("Search query must be at least 2 characters long");
  }
};
</script>

<style>
/* Global styles */
:root {
  --v-primary-base: #1867C0;
  --v-secondary-base: #5CBBF6;
}

body {
  font-family: 'Roboto', sans-serif;
  margin: 0;
  padding: 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

a {
  text-decoration: none;
}
</style>
