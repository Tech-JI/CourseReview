<template>
  <div class="page-container">
    <div class="course-search">
      <div class="search-header">
        <h1 v-if="department">{{ department }}</h1>
        <h1 v-else>Search Results For "{{ query }}"</h1>
      </div>

      <div v-if="!query" class="alert-box info-alert">
        <h3>Empty query string. Please enter a search query. Example: ENGR 101</h3>
      </div>
      <div v-else-if="query.length < 2" class="alert-box warning-alert">
        <h3>Query must be at least 2 characters long.</h3>
      </div>
      <div v-else-if="loading" class="loading">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else-if="error" class="error">
        <el-alert :title="error" type="error" show-icon />
      </div>
      <div v-else-if="courses.length === 0" class="alert-box warning-alert">
        <h3>Could not find any results. Please double-check your search query, and make sure the department and course
          number are correct.</h3>
      </div>
      <div v-else>
        <el-table :data="courses" style="width: 100%">
          <el-table-column label="Course" min-width="250">
            <template #default="scope">
              <router-link :to="`/course/${scope.row.id}`" class="course-link">
                {{ scope.row.course_code }}: {{ scope.row.course_title }}
              </router-link>
            </template>
          </el-table-column>

          <el-table-column :label="`Offered ${term}?`" width="180">
            <template #default="scope">
              <span v-if="scope.row.is_offered_in_current_term">Offered {{ term }}</span>
              <span v-else-if="scope.row.last_offered">Last offered {{ scope.row.last_offered }}</span>
            </template>
          </el-table-column>

          <el-table-column label="Instructors" min-width="180">
            <template #default="scope">
              <span v-if="scope.row.instructors && scope.row.instructors.length > 0">
                {{ scope.row.instructors.slice(0, 2).join(', ') }}
                <span v-if="scope.row.instructors.length > 2">...</span>
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column label="Distribs" min-width="120">
            <template #default="scope">
              <span v-for="(distrib, index) in scope.row.distribs" :key="index">
                {{ distrib.name }}{{ index < scope.row.distribs.length - 1 ? ', ' : '' }} </span>
            </template>
          </el-table-column>

          <el-table-column label="Reviews" width="100" align="center">
            <template #default="scope">
              {{ scope.row.review_count }}
            </template>
          </el-table-column>

          <el-table-column label="Quality" width="100" align="center">
            <template #default="scope">
              <template v-if="isAuthenticated && scope.row.quality_score !== undefined">
                {{ scope.row.quality_score }}
              </template>
              <router-link v-else to="/accounts/login/">Login to reveal</router-link>
            </template>
          </el-table-column>

          <el-table-column label="Layup" width="100" align="center">
            <template #default="scope">
              <template v-if="isAuthenticated && scope.row.difficulty_score !== undefined">
                {{ scope.row.difficulty_score }}
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

const query = ref('');
const department = ref('');
const courses = ref([]);
const term = ref('');
const loading = ref(true);
const error = ref(null);
const isAuthenticated = ref(false);

const fetchSearchResults = async () => {
  if (query.value.length < 2) return;

  loading.value = true;
  error.value = null;

  try {
    // Make sure we're using the full URL path
    const apiUrl = `/api/search/?q=${encodeURIComponent(query.value)}`;

    const response = await fetch(apiUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    courses.value = data.courses || [];
    department.value = data.department || '';
    term.value = data.term || '';

  } catch (e) {
    console.error("Error fetching search results:", e);
    error.value = e.message;
    courses.value = [];
  } finally {
    loading.value = false;
  }
};

// Watch for changes in the route query
watch(() => route.query.q, (newQuery) => {
  if (newQuery !== query.value) {
    query.value = newQuery || '';
    if (query.value.length >= 2) {
      fetchSearchResults();
    } else {
      courses.value = [];
      loading.value = false;
    }
  }
}, { immediate: true });

onMounted(async () => {
  query.value = route.query.q || '';

  if (query.value.length >= 2) {
    await fetchSearchResults();
  } else {
    loading.value = false;
  }
  await checkAuthentication();
});

const checkAuthentication = async () => {
  try {
    const response = await fetch('/api/user/status/');
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.value = data.isAuthenticated;
    } else {
      isAuthenticated.value = false;
    }
  } catch (e) {
    console.error('Error checking authentication:', e);
    isAuthenticated.value = false;
  }
};
</script>

<style scoped>
.course-search {
  width: 100%;
}

.search-header {
  margin-bottom: 20px;
}

.loading,
.error {
  margin: 2em 0;
}

.alert-box {
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid transparent;
  border-radius: 4px;
}

.info-alert {
  color: #31708f;
  background-color: #d9edf7;
  border-color: #bce8f1;
}

.warning-alert {
  color: #8a6d3b;
  background-color: #fcf8e3;
  border-color: #faebcc;
}

.course-link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.course-link:hover {
  text-decoration: underline;
}

.el-table {
  margin-bottom: 20px;
}
</style>
