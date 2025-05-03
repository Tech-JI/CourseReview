<template>
  <div class="app-container">
    <div class="search-container" v-if="showSearchBar">
      <form @submit.prevent="performSearch">
        <div class="input-group">
          <input type="text" class="form-control" v-model="searchQuery" placeholder="Search for courses (e.g., ENGR101)"
            aria-label="Search for courses">
          <button class="btn btn-primary" type="submit">Search</button>
        </div>
      </form>
    </div>
    <router-view></router-view>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const searchQuery = ref('');

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
      path: '/courses', // Navigate to the new courses page
      query: { code: query.toUpperCase() } // Use 'code' query param
    });
  } else {
    alert("Search query must be at least 2 characters long");
  }
};
</script>

<style>
.app-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.search-container {
  margin-bottom: 20px;
}

.input-group {
  display: flex;
}

.form-control {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px 0 0 4px;
}

.btn-primary {
  background-color: #007bff;
  border-color: #007bff;
  color: white;
  border-radius: 0 4px 4px 0;
}
</style>
