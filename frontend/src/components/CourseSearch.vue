<template>
  <div class="course-search">
    <!-- Title Section -->
    <div class="row">
      <div class="col-md-12">
        <h1 v-if="pageTitle">{{ pageTitle }}</h1>
        <h1 v-else>Browse Courses</h1>
        <p v-if="message" class="alert alert-info">{{ message }}</p>
      </div>
    </div>

    <!-- Filter/Sort Controls -->
    <div class="row filter-controls">
      <!-- Text Search -->
      <div class="col-md-4">
        <input type="text" class="form-control" v-model="currentQuery" @keyup.enter="applyFiltersAndSearch"
          placeholder="Search code, title...">
      </div>
      <!-- Distrib Filter -->
      <div class="col-md-3">
        <select class="form-control" v-model="selectedDistrib" @change="applyFiltersAndSearch">
          <option value="">All Distribs</option>
          <option v-for="distrib in distribs" :key="distrib.code" :value="distrib.code">
            {{ distrib.name }} ({{ distrib.code }})
          </option>
        </select>
      </div>
      <!-- Sort Options -->
      <div class="col-md-3">
        <select class="form-control" v-model="selectedSort" @change="applyFiltersAndSearch">
          <option value="code">Sort by Code</option>
          <option value="quality_desc" :disabled="!isAuthenticated">Quality (High to Low)</option>
          <option value="quality_asc" :disabled="!isAuthenticated">Quality (Low to High)</option>
          <option value="difficulty_desc" :disabled="!isAuthenticated">Difficulty/Layup (Easy to Hard)</option>
          <option value="difficulty_asc" :disabled="!isAuthenticated">Difficulty/Layup (Hard to Easy)</option>
        </select>
        <small v-if="!isAuthenticated" class="text-muted">Login required for score sorting.</small>
      </div>
    </div>

    <!-- Results Section -->
    <div class="row">
      <div class="col-md-12">
        <div v-if="loading" class="loading">
          <h3>Loading results...</h3>
        </div>
        <div v-else-if="error" class="error">
          <h3>Error: {{ error }}</h3>
          <p v-if="errorDetails">{{ errorDetails }}</p>
        </div>
        <div v-else-if="courses.length === 0 && (currentQuery || selectedDistrib || (selectedSort != 'code'))"
          class="alert alert-warning">
          <h3>Could not find any results matching your criteria.</h3>
        </div>
        <div v-else-if="courses.length === 0" class="alert alert-info">
          <h3>No courses found. Try broadening your search or changing filters.</h3>
        </div>
        <div v-else>
          <!-- Course Table -->
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Course</th>
                <th>Offered {{ term }}?</th>
                <th>Instructors</th>
                <th>Distribs</th>
                <th>Reviews</th>
                <th v-if="isAuthenticated">
                  Quality
                  <span v-if="selectedSort === 'quality_desc'">▼</span>
                  <span v-if="selectedSort === 'quality_asc'">▲</span>
                </th>
                <th v-if="isAuthenticated">
                  Layup
                  <span v-if="selectedSort === 'difficulty_desc'">▼</span>
                  <span v-if="selectedSort === 'difficulty_asc'">▲</span>
                </th>
                <th v-if="!isAuthenticated">Scores</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="course in courses" :key="course.id">
                <td>
                  <router-link :to="`/course/${course.id}`" class="course-link">
                    {{ course.course_code }}: {{ course.course_title }}
                  </router-link>
                  <p v-if="course.short_description" class="text-muted small">{{ course.short_description }}</p>
                </td>
                <td>
                  <span v-if="course.is_offered_in_current_term">Yes</span>
                  <span v-else-if="course.last_offered">Last: {{ course.last_offered }}</span>
                  <span v-else>No</span>
                </td>
                <td>
                  <span v-if="course.instructors && course.instructors.length > 0">
                    {{ course.instructors.slice(0, 2).join(', ') }}
                    <span v-if="course.instructors.length > 2">...</span>
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="course.distribs && course.distribs.length > 0">
                    {{course.distribs.map(d => d.name).join(', ')}}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>{{ course.review_count }}</td>
                <template v-if="isAuthenticated">
                  <td>{{ course.quality_score ?? 'N/A' }}</td>
                  <td>{{ course.difficulty_score ?? 'N/A' }}</td>
                </template>
                <td v-else colspan="2"><router-link to="/accounts/login/">Login to see</router-link></td>
              </tr>
            </tbody>
          </table>

          <!-- Pagination -->
          <nav v-if="totalPages > 1">
            <ul class="pagination">
              <li class="page-item" :class="{ disabled: currentPage === 1 }">
                <a class="page-link" href="#" @click.prevent="changePage(currentPage - 1)">&laquo; Prev</a>
              </li>
              <li class="page-item disabled">
                <span class="page-link">Page {{ currentPage }} of {{ totalPages }}</span>
              </li>
              <li class="page-item" :class="{ disabled: currentPage === totalPages }">
                <a class="page-link" href="#" @click.prevent="changePage(currentPage + 1)">Next &raquo;</a>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

// --- Reactive state ---
const courses = ref([]);
const term = ref('');
const loading = ref(true);
const error = ref(null);
const errorDetails = ref(null);
const message = ref(null);
const isAuthenticated = ref(false);
const department = ref('');
const distribs = ref([]);
const totalPages = ref(1);

// --- State reflecting user inputs/URL ---
const currentQuery = ref(route.query.q || '');
const selectedDistrib = ref(route.query.dist || '');
const selectedSort = ref(route.query.sort || 'code');
const currentPage = ref(parseInt(route.query.page, 10) || 1);

// Computed property for the page title
const pageTitle = computed(() => {
  if (department.value) {
    return `${department.value} (${currentQuery.value.toUpperCase()}) Courses`;
  } else if (currentQuery.value) {
    return `Search Results For "${currentQuery.value}"`;
  } else if (selectedDistrib.value) {
    const distName = distribs.value.find(d => d.code === selectedDistrib.value)?.name || selectedDistrib.value;
    return `Courses with Distrib: ${distName}`;
  } else if (selectedSort.value.startsWith('quality')) {
    return 'Courses Sorted by Quality';
  } else if (selectedSort.value.startsWith('difficulty')) {
    return 'Courses Sorted by Difficulty (Layup)';
  }
  return 'Browse All Courses';
});

const fetchSearchResults = async () => {
  loading.value = true;
  error.value = null;
  errorDetails.value = null;
  message.value = null;

  // Construct query parameters from component state
  const params = new URLSearchParams();
  if (currentQuery.value.trim()) params.append('q', currentQuery.value.trim());
  if (selectedDistrib.value) params.append('dist', selectedDistrib.value);
  if (selectedSort.value && selectedSort.value !== 'code') params.append('sort', selectedSort.value);
  if (currentPage.value > 1) params.append('page', currentPage.value.toString());

  try {
    const apiUrl = `/api/search/?${params.toString()}`;
    const response = await fetch(apiUrl);

    const data = await response.json();

    if (!response.ok) {
      errorDetails.value = data?.detail || `Status: ${response.status}`;
      throw new Error(`Failed to fetch results. ${errorDetails.value}`);
    }

    courses.value = data.courses || [];
    department.value = data.department || '';
    term.value = data.term || '';
    distribs.value = data.distribs || [];
    totalPages.value = data.total_pages || 1;
    message.value = data.message || null;

    // Update state based on API response
    selectedDistrib.value = data.selected_distrib || '';
    selectedSort.value = data.selected_sort || 'code';
    currentPage.value = data.current_page || 1;

  } catch (e) {
    console.error("Error fetching search results:", e);
    error.value = e.message;
    courses.value = [];
    totalPages.value = 1;
    currentPage.value = 1;
  } finally {
    loading.value = false;
  }
};

const checkAuthentication = async () => {
  try {
    const response = await fetch('/api/user/status/');
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.value = data.isAuthenticated;
      if (!isAuthenticated.value && (selectedSort.value.startsWith('quality') || selectedSort.value.startsWith('difficulty'))) {
        selectedSort.value = 'code';
      }
    } else {
      isAuthenticated.value = false;
    }
  } catch (e) {
    console.error('Error checking authentication:', e);
    isAuthenticated.value = false;
  }
};

const updateRouterQuery = () => {
  const queryParams = {};
  if (currentQuery.value.trim()) queryParams.q = currentQuery.value.trim();
  if (selectedDistrib.value) queryParams.dist = selectedDistrib.value;
  if (selectedSort.value && selectedSort.value !== 'code') queryParams.sort = selectedSort.value;
  if (currentPage.value > 1) queryParams.page = currentPage.value.toString();

  router.replace({ path: '/search', query: queryParams });
};

const applyFiltersAndSearch = () => {
  currentPage.value = 1;
  updateRouterQuery();
};

const changePage = (newPage) => {
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage;
    updateRouterQuery();
  }
};

// Watch for URL changes and update state
watch(
  () => [route.query.q, route.query.dist, route.query.sort, route.query.page],
  async ([newQ, newDist, newSort, newPage]) => {
    currentQuery.value = newQ || '';
    selectedDistrib.value = newDist || '';
    selectedSort.value = newSort || 'code';
    currentPage.value = parseInt(newPage, 10) || 1;

    await checkAuthentication();
    await fetchSearchResults();
  },
  { immediate: true }
);

onMounted(async () => {
  await checkAuthentication();
});
</script>

<style scoped>
.course-search {
  width: 100%;
  margin: 0 auto;
}

.filter-controls {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 5px;
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.filter-controls>div {
  flex-grow: 1;
}

.filter-controls .form-control {
  min-width: 150px;
}

.loading,
.error {
  text-align: center;
  margin: 2em;
}

.error p {
  color: #dc3545;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th,
td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
  vertical-align: top;
}

.course-link {
  font-weight: bold;
  color: #007bff;
  text-decoration: none;
}

.course-link:hover {
  text-decoration: underline;
}

th {
  background-color: #e9ecef;
  font-weight: bold;
}

th span {
  font-size: 0.8em;
  margin-left: 4px;
}

.alert {
  padding: 15px;
  margin-top: 10px;
  margin-bottom: 20px;
  border: 1px solid transparent;
  border-radius: 4px;
}

.alert-info {
  color: #0c5460;
  background-color: #d1ecf1;
  border-color: #bee5eb;
}

.alert-warning {
  color: #856404;
  background-color: #fff3cd;
  border-color: #ffeeba;
}

.text-muted {
  color: #6c757d !important;
}

.small {
  font-size: 0.875em;
}

.pagination {
  display: flex;
  padding-left: 0;
  list-style: none;
  border-radius: 0.25rem;
  justify-content: center;
  margin-top: 20px;
}

.page-item.disabled .page-link {
  color: #6c757d;
  pointer-events: none;
  cursor: auto;
  background-color: #fff;
  border-color: #dee2e6;
}

.page-item .page-link {
  position: relative;
  display: block;
  padding: 0.5rem 0.75rem;
  margin-left: -1px;
  line-height: 1.25;
  color: #007bff;
  background-color: #fff;
  border: 1px solid #dee2e6;
  cursor: pointer;
}

.page-item .page-link:hover {
  z-index: 2;
  color: #0056b3;
  text-decoration: none;
  background-color: #e9ecef;
  border-color: #dee2e6;
}
</style>
