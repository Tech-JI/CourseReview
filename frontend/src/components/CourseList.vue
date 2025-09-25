<template>
  <div class="min-h-full">
    <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">Courses</h1>
        <p class="mt-2 text-sm text-gray-700">
          Browse and discover courses at University of Michigan - Joint
          Institute
        </p>
      </div>

      <div class="mb-8">
        <div class="overflow-hidden bg-white shadow sm:rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-base font-semibold leading-6 text-gray-900 mb-4">
              Filters & Sorting
            </h3>
            <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
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
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  @change="applyFiltersAndSort"
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

              <div>
                <label
                  for="code"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Course Code
                </label>
                <input
                  id="code"
                  v-model="filters.code"
                  type="text"
                  placeholder="e.g., ECE215"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  @keyup.enter="applyFiltersAndSort"
                />
              </div>

              <div v-if="isAuthenticated">
                <label
                  for="min_quality"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Min Quality
                </label>
                <input
                  id="min_quality"
                  v-model.number="filters.min_quality"
                  type="number"
                  min="0"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  @change="applyFiltersAndSort"
                />
              </div>

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
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  @change="applyFiltersAndSort"
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

              <div>
                <label
                  for="sort_order"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Order
                </label>
                <select
                  id="sort_order"
                  v-model="sorting.sort_order"
                  class="mt-1 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  @change="applyFiltersAndSort"
                >
                  <option value="asc">Ascending</option>
                  <option value="desc">Descending</option>
                </select>
              </div>
            </div>

            <div class="mt-6 flex gap-3">
              <button
                class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                @click="applyFiltersAndSort"
              >
                Apply Filters
              </button>
              <button
                class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                @click="resetFiltersAndSort"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      </div>

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

      <div v-else-if="courses.length > 0">
        <div class="mb-4 text-sm text-gray-700">
          Showing {{ courses.length }} of {{ pagination.total_courses }} courses
        </div>

        <div class="overflow-hidden bg-white shadow sm:rounded-md">
          <ul class="divide-y divide-gray-200">
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

                    <div class="ml-4 flex-shrink-0 flex items-center space-x-4">
                      <div class="text-center">
                        <div class="text-2xl font-bold text-gray-900">
                          {{ course.review_count }}
                        </div>
                        <div class="text-xs text-gray-500">Reviews</div>
                      </div>

                      <div v-if="isAuthenticated" class="text-center">
                        <div class="text-2xl font-bold text-indigo-600">
                          {{
                            course.quality_score > 0
                              ? course.quality_score.toFixed(1)
                              : "N/A"
                          }}
                        </div>
                        <div class="text-xs text-gray-500">Quality</div>
                      </div>

                      <div v-if="isAuthenticated" class="text-center">
                        <div class="text-2xl font-bold text-green-600">
                          {{
                            course.difficulty_score > 0
                              ? course.difficulty_score.toFixed(1)
                              : "N/A"
                          }}
                        </div>
                        <div class="text-xs text-gray-500">Difficulty</div>
                      </div>

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
              :disabled="pagination.current_page <= 1"
              class="relative inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus-visible:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="changePage(pagination.current_page - 1)"
            >
              Previous
            </button>
            <button
              :disabled="pagination.current_page >= pagination.total_pages"
              class="relative ml-3 inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus-visible:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="changePage(pagination.current_page + 1)"
            >
              Next
            </button>
          </div>
        </nav>
      </div>

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
            class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            @click="resetFiltersAndSort"
          >
            Clear all filters
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuth } from "../composables/useAuth";
import { useCourses } from "../composables/useCourses";
import {
  ExclamationTriangleIcon,
  AcademicCapIcon,
  UsersIcon,
} from "@heroicons/vue/24/outline";

const route = useRoute();
const router = useRouter();

const {
  courses,
  departments,
  loading,
  error,
  pagination,
  filters,
  sorting,
  fetchDepartments,
  fetchCourses,
  getQueryObject,
  applyFiltersAndSort: applyFiltersAndSortFn,
  resetFiltersAndSort: resetFiltersAndSortFn,
  changePage: changePageFn,
  syncStateFromQuery,
} = useCourses();
const { isAuthenticated, checkAuthentication } = useAuth();
const currentTerm = ref("Current");

const updateRoute = () => {
  const query = getQueryObject(isAuthenticated.value);
  router.push({ path: "/courses", query });
};

const applyFiltersAndSortLocal = () => {
  applyFiltersAndSortFn();
  updateRoute();
};

const applyFiltersAndSort = () => {
  applyFiltersAndSortLocal();
};

const resetFiltersAndSortLocal = () => {
  resetFiltersAndSortFn();
  updateRoute();
};

const resetFiltersAndSort = () => {
  resetFiltersAndSortLocal();
};

const changePageLocal = (newPage) => {
  changePageFn(newPage);
  updateRoute();
};

const changePage = (newPage) => {
  changePageLocal(newPage);
};

onMounted(async () => {
  await checkAuthentication();
  await fetchDepartments();
  syncStateFromQuery(route.query);
  await fetchCourses(isAuthenticated.value);
});

watch(
  () => route.query,
  (newQuery) => {
    syncStateFromQuery(newQuery);
    fetchCourses(isAuthenticated.value);
  },
);
</script>
