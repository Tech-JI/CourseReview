<template>
  <div class="course-search">
    <div class="row">
      <div class="col-md-12">
        <h1 v-if="department">{{ department }}</h1>
        <h1 v-else>Search Results For "{{ query }}"</h1>
      </div>
    </div>

    <div class="row">
      <div class="col-md-12">
        <div v-if="!query" class="alert alert-info">
          <h3>Empty query string. Please enter a search query. Example: ENGR 101</h3>
        </div>
        <div v-else-if="query.length < 2" class="alert alert-warning">
          <h3>Query must be at least 2 characters long.</h3>
        </div>
        <div v-else-if="loading" class="loading">
          <h3>Loading search results...</h3>
        </div>
        <div v-else-if="error" class="error">
          <h3>Error: {{ error }}</h3>
        </div>
        <div v-else-if="courses.length === 0" class="alert alert-warning">
          <h3>Could not find any results. Please double-check your search query, and make sure the department and course
            number are correct.</h3>
        </div>
        <div v-else>
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Course</th>
                <th>Offered {{ term }}?</th>
                <th>Instructors</th>
                <th>Distribs</th>
                <th>Reviews</th>
                <th>Quality</th>
                <th>Layup</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="course in courses" :key="course.id" @click="goToCourse(course.id)" role="button">
                <td><a>{{ course.course_code }}: {{ course.course_title }}</a></td>
                <td>
                  <span v-if="course.is_offered_in_current_term">Offered {{ term }}</span>
                  <span v-else-if="course.last_offered">Last offered {{ course.last_offered }}</span>
                </td>
                <td>
                  <span v-if="course.instructors && course.instructors.length > 0">
                    {{ course.instructors.slice(0, 2).join(', ') }}
                    <span v-if="course.instructors.length > 2">...</span>
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-for="(distrib, index) in course.distribs" :key="index">
                    {{ distrib.name }}{{ index < course.distribs.length - 1 ? ', ' : '' }} </span>
                </td>
                <td>{{ course.review_count }}</td>
                <td v-if="isAuthenticated && course.quality_score !== undefined">{{ course.quality_score }}</td>
                <td v-if="isAuthenticated && course.difficulty_score !== undefined">{{ course.difficulty_score }}</td>
                <td v-else colspan="2"><a href="/accounts/signup/">Signup to reveal</a></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

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
  console.log("CourseSearch mounted, query:", query.value);

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

const goToCourse = (courseId) => {
  router.push(`/course/${courseId}`);
};
</script>

<style scoped>
.course-search {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.loading,
.error {
  text-align: center;
  margin: 2em;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

tr:hover {
  background-color: #f5f5f5;
  cursor: pointer;
}

th {
  background-color: #f2f2f2;
  font-weight: bold;
}

.alert {
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid transparent;
  border-radius: 4px;
}

.alert-info {
  color: #31708f;
  background-color: #d9edf7;
  border-color: #bce8f1;
}

.alert-warning {
  color: #8a6d3b;
  background-color: #fcf8e3;
  border-color: #faebcc;
}
</style>
