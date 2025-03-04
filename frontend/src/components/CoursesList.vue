<template>
  <div class="courses-list">
    <div class="row">
      <div class="col-md-10">
        <h1>{{ term }} {{ courseType }}</h1>
      </div>
      <div class="col-md-2 text-right">
        <select class="form-control" v-model="selectedDistrib" @change="fetchCourses">
          <option value="">Filter by distrib</option>
          <option v-for="distrib in distribs" :key="distrib.code" :value="distrib.code">
            {{ distrib.name.toUpperCase() }}
          </option>
        </select>
      </div>
    </div>

    <div class="row">
      <div class="col-md-12">
        <table class="table">
          <thead>
            <tr>
              <th class="text-center">{{ sort === 'best' ? 'Quality Score' : 'Layup Score' }}</th>
              <th>Course</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="course in courses" :key="course.id">
              <td class="text-center">
                <span class="vote-arrow glyphicon glyphicon-chevron-up"
                  :class="{ selected: course.quality_vote?.is_upvote }"
                  @click="vote(course.id, 1, sort === 'best')"></span>
                <h2 class="score">{{ sort === 'best' ? course.quality_score : course.difficulty_score }}</h2>
                <span class="vote-arrow glyphicon glyphicon-chevron-down"
                  :class="{ selected: course.quality_vote?.is_downvote }"
                  @click="vote(course.id, -1, sort === 'best')"></span>
              </td>
              <td>
                <h3>
                  <router-link :to="`/course/${course.id}`">{{ course.course_code }}: {{ course.course_title
                  }}</router-link>
                </h3>
                <h5>
                  {{ course.review_count }} reviews
                  <span v-if="course.distribs.length"> | {{course.distribs.map(d => d.name).join(', ')}}</span>
                  <span v-if="course.offered_times_string"> | Offered during {{ course.offered_times_string }}</span>
                </h5>
                <div v-if="course.short_description">
                  <p>
                    {{ course.short_description.length > 250 ?
                      course.short_description.substring(0, 250) + '...' :
                      course.short_description
                    }}
                    <router-link :to="`/course/${course.id}`">(see more)</router-link>
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <nav>
      <ul class="pager">
        <li :class="{ disabled: currentPage === 1 }">
          <a @click="changePage(currentPage - 1)">&larr; Previous</a>
        </li>
        <li>{{ currentPage }} of {{ totalPages }}</li>
        <li :class="{ disabled: currentPage === totalPages }">
          <a @click="changePage(currentPage + 1)">Next &rarr;</a>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const sort = ref(route.params.sort);
const courses = ref([]);
const term = ref('');
const courseType = ref('');
const distribs = ref([]);
const selectedDistrib = ref('');
const currentPage = ref(1);
const totalPages = ref(1);
const loading = ref(true);
const error = ref(null);

const fetchCourses = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch(
      `/api/${sort.value}/?page=${currentPage.value}&dist=${selectedDistrib.value}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    courses.value = data.courses;
    term.value = data.term;
    courseType.value = data.course_type;
    distribs.value = data.distribs;
    selectedDistrib.value = data.selected_distrib || '';
    currentPage.value = data.current_page;
    totalPages.value = data.total_pages;
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    fetchCourses();
  }
};

const vote = async (courseId, value, isQuality) => {
  try {
    const response = await fetch(`/api/course/${courseId}/vote`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify({
        value,
        forLayup: !isQuality
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    await fetchCourses(); // Refresh data after voting
  } catch (e) {
    console.error('Error voting:', e);
    alert('You must be logged in to vote');
  }
};

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

onMounted(() => {
  fetchCourses();
});

watch(() => route.params.sort, (newSort) => {
  sort.value = newSort;
  fetchCourses();
});
</script>

<style scoped>
.courses-list {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.vote-arrow {
  cursor: pointer;
  color: gray;
}

.vote-arrow.selected {
  color: green;
}

.score {
  margin: 10px 0;
}

.pager {
  display: flex;
  justify-content: center;
  margin: 20px 0;
}

.pager li {
  margin: 0 10px;
}

.pager li.disabled a {
  color: #ccc;
  pointer-events: none;
}

.pager li a {
  cursor: pointer;
}
</style>
