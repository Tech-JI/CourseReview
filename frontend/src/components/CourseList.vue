<template>
  <div class="course-list-container">
    <h1>Courses</h1>

    <!-- Filters and Sorting -->
    <div class="controls">
      <!-- Department Filter -->
      <div class="control-group">
        <label for="department">Department:</label>
        <select id="department" v-model="filters.department" @change="applyFiltersAndSort">
          <option value="">All Departments</option>
          <option v-for="dept in departments" :key="dept.code" :value="dept.code">
            {{ dept.code }} - {{ dept.name }} ({{ dept.count }})
          </option>
        </select>
      </div>

      <!-- Course Code Search -->
      <div class="control-group">
        <label for="code">Course Code:</label>
        <input type="text" id="code" v-model="filters.code" @keyup.enter="applyFiltersAndSort" placeholder="e.g., ECE215" />
      </div>

      <!-- Min Quality Filter (Auth Only) -->
      <div class="control-group" v-if="isAuthenticated">
        <label for="min_quality">Min Quality:</label>
        <input type="number" id="min_quality" v-model.number="filters.min_quality" @change="applyFiltersAndSort" min="0"/>
      </div>

      <!-- Sorting -->
      <div class="control-group">
        <label for="sort_by">Sort By:</label>
        <select id="sort_by" v-model="sorting.sort_by" @change="applyFiltersAndSort">
          <option value="course_code">Course Code</option>
          <option value="num_reviews">Number of Reviews</option>
          <option v-if="isAuthenticated" value="quality_score">Quality Score</option>
          <option v-if="isAuthenticated" value="difficulty_score">Difficulty (Layup) Score</option>
        </select>
        <select v-model="sorting.sort_order" @change="applyFiltersAndSort">
          <option value="asc">Ascending</option>
          <option value="desc">Descending</option>
        </select>
      </div>

      <button @click="applyFiltersAndSort">Apply</button>
      <button @click="resetFiltersAndSort">Reset</button>
    </div>

    <!-- Loading / Error State -->
    <div v-if="loading" class="loading">Loading courses...</div>
    <div v-else-if="error" class="error">Error fetching courses: {{ error }}</div>

    <!-- Course Results Table -->
    <div v-else-if="courses.length > 0">
      <p>Showing {{ courses.length }} of {{ pagination.total_courses }} courses.</p>
      <table class="table table-hover">
        <thead>
          <tr>
            <th>Course</th>
            <th>Offered {{ currentTerm }}?</th>
            <th>Instructors</th>
            <th>Distribs</th>
            <th>Reviews</th>
            <th v-if="isAuthenticated">Quality</th>
            <th v-if="isAuthenticated">Difficulty</th>
            <th v-if="!isAuthenticated">Scores</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in courses" :key="course.id">
            <td>
              <router-link :to="`/course/${course.id}`" class="course-link">
                {{ course.course_code }}: {{ course.course_title }}
              </router-link>
            </td>
            <td>
              <span v-if="course.is_offered_in_current_term">Yes</span>
              <span v-else-if="course.last_offered">Last: {{ course.last_offered }}</span>
               <span v-else>-</span>
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
               {{ course.distribs.map(d => d.name).join(', ') }}
              </span>
               <span v-else>-</span>
            </td>
            <td>{{ course.review_count }}</td>
            <td v-if="isAuthenticated">{{ course.quality_score ?? 'N/A' }}</td>
            <td v-if="isAuthenticated">{{ course.difficulty_score ?? 'N/A' }}</td>
             <td v-if="!isAuthenticated"><router-link to="/accounts/login/">Login</router-link></td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="pagination-controls">
        <button @click="changePage(pagination.current_page - 1)" :disabled="pagination.current_page <= 1">
          &larr; Previous
        </button>
        <span>Page {{ pagination.current_page }} of {{ pagination.total_pages }}</span>
        <button @click="changePage(pagination.current_page + 1)" :disabled="pagination.current_page >= pagination.total_pages">
          Next &rarr;
        </button>
      </div>
    </div>

    <!-- No Results -->
    <div v-else class="no-results">
      No courses found matching your criteria.
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const courses = ref([]);
const departments = ref([]);
const loading = ref(false);
const error = ref(null);
const isAuthenticated = ref(false);
const currentTerm = ref("Current"); // TODO: Maybe fetch current term?

const pagination = reactive({
  current_page: 1,
  total_pages: 1,
  total_courses: 0,
  limit: 20, // Should match backend LIMITS['courses']
});

const filters = reactive({
  department: '',
  code: '',
  min_quality: null,
  min_difficulty: null, // Consider adding if needed
});

const sorting = reactive({
  sort_by: 'course_code',
  sort_order: 'asc',
});

// --- API Fetching ---

const fetchDepartments = async () => {
  try {
    const response = await fetch('/api/departments/');
    if (!response.ok) throw new Error('Failed to fetch departments');
    departments.value = await response.json();
  } catch (e) {
    console.error("Error fetching departments:", e);
    // Non-critical error, maybe show a message?
  }
};

const fetchCourses = async () => {
  loading.value = true;
  error.value = null;

  // Construct query parameters from reactive refs
  const params = new URLSearchParams();
  if (filters.department) params.append('department', filters.department);
  if (filters.code) params.append('code', filters.code.trim());
  if (filters.min_quality && isAuthenticated.value) params.append('min_quality', filters.min_quality);
  // if (filters.min_difficulty && isAuthenticated.value) params.append('min_difficulty', filters.min_difficulty);

  params.append('sort_by', sorting.sort_by);
  params.append('sort_order', sorting.sort_order);
  params.append('page', pagination.current_page);

  try {
    const response = await fetch(`/api/courses/?${params.toString()}`);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    courses.value = data.courses;
    pagination.current_page = data.pagination.current_page;
    pagination.total_pages = data.pagination.total_pages;
    pagination.total_courses = data.pagination.total_courses;
    pagination.limit = data.pagination.limit;
  } catch (e) {
    console.error("Error fetching courses:", e);
    error.value = e.message;
    courses.value = []; // Clear courses on error
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
      // Reset sort if user logs out and was sorting by auth-only field
      if (!isAuthenticated.value && (sorting.sort_by === 'quality_score' || sorting.sort_by === 'difficulty_score')) {
        sorting.sort_by = 'course_code';
      }
    } else {
      isAuthenticated.value = false;
    }
  } catch (e) {
    console.error('Error checking authentication:', e);
    isAuthenticated.value = false;
  }
};

// --- Event Handling & Logic ---

const updateRoute = () => {
  const query = {};
  if (filters.department) query.department = filters.department;
  if (filters.code) query.code = filters.code.trim();
  if (filters.min_quality && isAuthenticated.value) query.min_quality = filters.min_quality;
  // if (filters.min_difficulty && isAuthenticated.value) query.min_difficulty = filters.min_difficulty;

  if (sorting.sort_by !== 'course_code' || sorting.sort_order !== 'asc') {
     query.sort_by = sorting.sort_by;
     query.sort_order = sorting.sort_order;
  }
  if (pagination.current_page > 1) query.page = pagination.current_page;

  router.push({ path: '/courses', query });
};

const applyFiltersAndSort = () => {
   pagination.current_page = 1; // Reset to first page when filters change
   updateRoute();
};

const resetFiltersAndSort = () => {
   filters.department = '';
   filters.code = '';
   filters.min_quality = null;
   filters.min_difficulty = null;
   sorting.sort_by = 'course_code';
   sorting.sort_order = 'asc';
   pagination.current_page = 1;
   updateRoute();
}

const changePage = (newPage) => {
  if (newPage >= 1 && newPage <= pagination.total_pages) {
    pagination.current_page = newPage;
    updateRoute();
  }
};

// --- Lifecycle and Watchers ---

onMounted(async () => {
  await checkAuthentication();
  await fetchDepartments();
  // Sync state from initial route query parameters
  syncStateFromRoute(route.query);
  await fetchCourses(); // Fetch initial data based on URL state
});

// Watch for route changes to re-fetch data
watch(() => route.query, (newQuery) => {
   syncStateFromRoute(newQuery);
   fetchCourses();
});

// Helper to update component state from URL query params
const syncStateFromRoute = (query) => {
    filters.department = query.department || '';
    filters.code = query.code || '';
    filters.min_quality = query.min_quality ? parseInt(query.min_quality, 10) : null;
    // filters.min_difficulty = query.min_difficulty ? parseInt(query.min_difficulty, 10) : null;
    sorting.sort_by = query.sort_by || 'course_code';
    sorting.sort_order = query.sort_order || 'asc';
    pagination.current_page = query.page ? parseInt(query.page, 10) : 1;

   // Ensure sort_by is valid if user is not authenticated
   if (!isAuthenticated.value && (sorting.sort_by === 'quality_score' || sorting.sort_by === 'difficulty_score')) {
     sorting.sort_by = 'course_code'; // Default if auth changed
   }
};

</script>

<style scoped>
.course-list-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f8f8; /* Light background for controls */
  border-radius: 5px;
}

.control-group {
   display: flex;
   flex-direction: column; /* Stack label and input */
   gap: 5px;
}

.control-group label {
  font-weight: bold;
  font-size: 0.9em;
}

 .control-group input,
 .control-group select {
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
 }

.loading,
.error,
.no-results {
  text-align: center;
  margin: 2em;
  padding: 1em;
  background-color: #f0f0f0;
  border-radius: 5px;
}
.error {
  color: red;
  background-color: #ffe0e0;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}

th,
td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

th {
  background-color: #e9ecef; /* Slightly darker header */
  font-weight: bold;
}

tr:hover {
  background-color: #f5f5f5;
}

.course-link {
  color: inherit;
  text-decoration: none;
  font-weight: 500;
}

.course-link:hover {
  text-decoration: underline;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}
.pagination-controls button {
   padding: 5px 10px;
}
.pagination-controls button:disabled {
   cursor: not-allowed;
   opacity: 0.6;
}
</style>
