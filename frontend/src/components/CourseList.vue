<template>
  <div class="min-h-full">
    <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <!-- Page header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">Courses</h1>
        <p class="mt-2 text-sm text-gray-700">
          Browse and discover courses at University of Michigan - Joint
          Institute
        </p>
      </div>

      <!-- Filters Card -->
      <div class="mb-8">
        <div class="overflow-hidden bg-white shadow sm:rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-base font-semibold leading-6 text-gray-900 mb-4">
              Filters & Sorting
            </h3>
            <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
              <!-- Department Filter -->
              <div>
                <label
                  for="department"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Department
                </label>
                <select
                  id="department"
                  v-model="filters.department"
                  @change="applyFiltersAndSort"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
                >
                  <option value="">All Departments</option>
                  <option
                    v-for="dept in departments"
                    :key="dept.code"
                    :value="dept.code"
                  >
                    {{ dept.code }} - {{ dept.name }} ({{ dept.count }})
                  </option>
                </select>
              </div>

              <!-- Course Code Search -->
              <div>
                <label
                  for="code"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Course Code
                </label>
                <input
                  type="text"
                  id="code"
                  v-model="filters.code"
                  @keyup.enter="applyFiltersAndSort"
                  placeholder="e.g., ECE215"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                />
              </div>

              <!-- Min Quality Filter (Auth Only) -->
              <div v-if="isAuthenticated">
                <label
                  for="min_quality"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Min Quality
                </label>
                <input
                  type="number"
                  id="min_quality"
                  v-model.number="filters.min_quality"
                  @change="applyFiltersAndSort"
                  min="0"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                />
              </div>

              <!-- Sort By -->
              <div>
                <label
                  for="sort_by"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Sort By
                </label>
                <select
                  id="sort_by"
                  v-model="sorting.sort_by"
                  @change="applyFiltersAndSort"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
                >
                  <option value="course_code">Course Code</option>
                  <option value="num_reviews">Number of Reviews</option>
                  <option v-if="isAuthenticated" value="quality_score">
                    Quality Score
                  </option>
                  <option v-if="isAuthenticated" value="difficulty_score">
                    Difficulty (Layup) Score
                  </option>
                </select>
              </div>

              <!-- Sort Order -->
              <div>
                <label
                  for="sort_order"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Order
                </label>
                <select
                  v-model="sorting.sort_order"
                  @change="applyFiltersAndSort"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
                >
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
                </select>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="mt-6 flex gap-3">
              <button
                @click="applyFiltersAndSort"
                class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              >
                Apply Filters
              </button>
              <button
                @click="resetFiltersAndSort"
                class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-12">
        <div
          class="inline-flex items-center px-4 py-2 font-semibold leading-6 text-sm shadow rounded-md text-white bg-indigo-500"
        >
          <svg
            class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          Loading courses...
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="rounded-md bg-red-50 p-4">
        <div class="flex">
          <ExclamationTriangleIcon
            class="h-5 w-5 text-red-400"
            aria-hidden="true"
          />
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">
              Error loading courses
            </h3>
            <div class="mt-2 text-sm text-red-700">{{ error }}</div>
          </div>
        </div>
      </div>

      <!-- Course Results -->
      <div v-else-if="courses.length > 0">
        <!-- Results Count -->
        <div class="mb-4 text-sm text-gray-700">
          Showing {{ courses.length }} of {{ pagination.total_courses }} courses
        </div>

        <!-- Course Cards -->
        <div class="overflow-hidden bg-white shadow sm:rounded-md">
          <ul role="list" class="divide-y divide-gray-200">
            <li v-for="course in courses" :key="course.id">
              <router-link
                :to="`/course/${course.id}`"
                class="block hover:bg-gray-50"
              >
                <div class="px-4 py-4 sm:px-6">
                  <div class="flex items-center justify-between">
                    <div class="flex-1 min-w-0">
                      <h3 class="text-lg font-medium text-indigo-600 truncate">
                        {{ course.course_code }}: {{ course.course_title }}
                      </h3>
                      <div class="mt-1 flex items-center text-sm text-gray-500">
                        <!-- Offered Status -->
                        <span
                          v-if="course.is_offered_in_current_term"
                          class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
                        >
                          Offered {{ currentTerm }}
                        </span>
                        <span
                          v-else-if="course.last_offered"
                          class="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800"
                        >
                          Last: {{ course.last_offered }}
                        </span>
                        <span
                          v-else
                          class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800"
                        >
                          Not Recently Offered
                        </span>

                        <!-- Instructors -->
                        <span
                          v-if="
                            course.instructors && course.instructors.length > 0
                          "
                          class="ml-4"
                        >
                          <UsersIcon class="h-4 w-4 inline mr-1" />
                          {{ course.instructors.slice(0, 2).join(", ") }}
                          <span v-if="course.instructors.length > 2">...</span>
                        </span>
                      </div>

                      <!-- Distribs -->
                      <div
                        v-if="course.distribs && course.distribs.length > 0"
                        class="mt-2"
                      >
                        <span
                          v-for="distrib in course.distribs.slice(0, 3)"
                          :key="distrib.name"
                          class="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10 mr-2"
                        >
                          {{ distrib.name }}
                        </span>
                        <span
                          v-if="course.distribs.length > 3"
                          class="text-xs text-gray-500"
                        >
                          +{{ course.distribs.length - 3 }} more
                        </span>
                      </div>
                    </div>

                    <!-- Stats -->
                    <div class="ml-4 flex-shrink-0 flex items-center space-x-4">
                      <!-- Reviews -->
                      <div class="text-center">
                        <div class="text-2xl font-bold text-gray-900">
                          {{ course.review_count }}
                        </div>
                        <div class="text-xs text-gray-500">Reviews</div>
                      </div>

                      <!-- Quality Score (Auth Only) -->
                      <div v-if="isAuthenticated" class="text-center">
                        <div class="text-2xl font-bold text-indigo-600">
                          {{ course.quality_score ?? "N/A" }}
                        </div>
                        <div class="text-xs text-gray-500">Quality</div>
                      </div>

                      <!-- Difficulty Score (Auth Only) -->
                      <div v-if="isAuthenticated" class="text-center">
                        <div class="text-2xl font-bold text-green-600">
                          {{ course.difficulty_score ?? "N/A" }}
                        </div>
                        <div class="text-xs text-gray-500">Difficulty</div>
                      </div>

                      <!-- Login prompt for non-auth users -->
                      <div v-if="!isAuthenticated" class="text-center">
                        <router-link
                          to="/accounts/login/"
                          class="text-sm text-indigo-600 hover:text-indigo-900 font-medium"
                        >
                          Login for scores
                        </router-link>
                      </div>
                    </div>
                  </div>
                </div>
              </router-link>
            </li>
          </ul>
        </div>

        <!-- Pagination -->
        <nav
          class="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 mt-6"
          aria-label="Pagination"
        >
          <div class="hidden sm:block">
            <p class="text-sm text-gray-700">
              Page
              <span class="font-medium">{{ pagination.current_page }}</span> of
              <span class="font-medium">{{ pagination.total_pages }}</span>
            </p>
          </div>
          <div class="flex flex-1 justify-between sm:justify-end">
            <button
              @click="changePage(pagination.current_page - 1)"
              :disabled="pagination.current_page <= 1"
              class="relative inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus-visible:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              @click="changePage(pagination.current_page + 1)"
              :disabled="pagination.current_page >= pagination.total_pages"
              class="relative ml-3 inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus-visible:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </nav>
      </div>

      <!-- No Results -->
      <div v-else class="text-center py-12">
        <div class="mx-auto h-12 w-12 text-gray-400">
          <AcademicCapIcon class="h-12 w-12" />
        </div>
        <h3 class="mt-2 text-sm font-semibold text-gray-900">
          No courses found
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          Try adjusting your search criteria or filters.
        </p>
        <div class="mt-6">
          <button
            @click="resetFiltersAndSort"
            class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          >
            Clear all filters
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ExclamationTriangleIcon,
  AcademicCapIcon,
  UsersIcon,
} from "@heroicons/vue/24/outline";

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
  department: "",
  code: "",
  min_quality: null,
  min_difficulty: null, // Consider adding if needed
});

const sorting = reactive({
  sort_by: "course_code",
  sort_order: "asc",
});

// --- API Fetching ---

const fetchDepartments = async () => {
  try {
    const response = await fetch("/api/departments/");
    if (!response.ok) throw new Error("Failed to fetch departments");
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
  if (filters.department) params.append("department", filters.department);
  if (filters.code) params.append("code", filters.code.trim());
  if (filters.min_quality && isAuthenticated.value)
    params.append("min_quality", filters.min_quality);
  // if (filters.min_difficulty && isAuthenticated.value) params.append('min_difficulty', filters.min_difficulty);

  params.append("sort_by", sorting.sort_by);
  params.append("sort_order", sorting.sort_order);
  params.append("page", pagination.current_page);

  try {
    const response = await fetch(`/api/courses/?${params.toString()}`);
    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: "Unknown error" }));
      throw new Error(
        errorData.detail || `HTTP error! status: ${response.status}`,
      );
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
    const response = await fetch("/api/user/status/");
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.value = data.isAuthenticated;
      // Reset sort if user logs out and was sorting by auth-only field
      if (
        !isAuthenticated.value &&
        (sorting.sort_by === "quality_score" ||
          sorting.sort_by === "difficulty_score")
      ) {
        sorting.sort_by = "course_code";
      }
    } else {
      isAuthenticated.value = false;
    }
  } catch (e) {
    console.error("Error checking authentication:", e);
    isAuthenticated.value = false;
  }
};

// --- Event Handling & Logic ---

const updateRoute = () => {
  const query = {};
  if (filters.department) query.department = filters.department;
  if (filters.code) query.code = filters.code.trim();
  if (filters.min_quality && isAuthenticated.value)
    query.min_quality = filters.min_quality;
  // if (filters.min_difficulty && isAuthenticated.value) query.min_difficulty = filters.min_difficulty;

  if (sorting.sort_by !== "course_code" || sorting.sort_order !== "asc") {
    query.sort_by = sorting.sort_by;
    query.sort_order = sorting.sort_order;
  }
  if (pagination.current_page > 1) query.page = pagination.current_page;

  router.push({ path: "/courses", query });
};

const applyFiltersAndSort = () => {
  pagination.current_page = 1; // Reset to first page when filters change
  updateRoute();
};

const resetFiltersAndSort = () => {
  filters.department = "";
  filters.code = "";
  filters.min_quality = null;
  filters.min_difficulty = null;
  sorting.sort_by = "course_code";
  sorting.sort_order = "asc";
  pagination.current_page = 1;
  updateRoute();
};

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
watch(
  () => route.query,
  (newQuery) => {
    syncStateFromRoute(newQuery);
    fetchCourses();
  },
);

// Helper to update component state from URL query params
const syncStateFromRoute = (query) => {
  filters.department = query.department || "";
  filters.code = query.code || "";
  filters.min_quality = query.min_quality
    ? parseInt(query.min_quality, 10)
    : null;
  // filters.min_difficulty = query.min_difficulty ? parseInt(query.min_difficulty, 10) : null;
  sorting.sort_by = query.sort_by || "course_code";
  sorting.sort_order = query.sort_order || "asc";
  pagination.current_page = query.page ? parseInt(query.page, 10) : 1;

  // Ensure sort_by is valid if user is not authenticated
  if (
    !isAuthenticated.value &&
    (sorting.sort_by === "quality_score" ||
      sorting.sort_by === "difficulty_score")
  ) {
    sorting.sort_by = "course_code"; // Default if auth changed
  }
};
</script>
