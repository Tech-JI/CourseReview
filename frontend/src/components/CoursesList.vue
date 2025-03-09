<template>
  <div class="page-container">
    <el-skeleton :loading="loading" animated>
      <template #template>
        <div style="padding: 20px">
          <el-skeleton-item variant="h1" style="width: 40%" />
          <div style="margin-top: 20px">
            <el-skeleton-item variant="text" style="width: 100%" />
            <el-skeleton-item variant="text" style="width: 100%" />
            <el-skeleton-item variant="text" style="width: 100%" />
          </div>
        </div>
      </template>

      <template #default>
        <el-alert v-if="error" :title="error" type="error" show-icon />

        <div v-else class="courses-list">
          <div class="list-header">
            <h1>{{ term }} {{ courseType }}</h1>

            <el-select v-model="selectedDistrib" placeholder="Filter by distrib" @change="fetchCourses" clearable>
              <el-option v-for="distrib in distribs" :key="distrib.code" :label="distrib.name.toUpperCase()"
                :value="distrib.code" />
            </el-select>
          </div>

          <el-card v-for="course in courses" :key="course.id" class="course-card">
            <div class="course-card-content">
              <div class="score-column">
                <div class="score-box">
                  <i class="fa-solid fa-chevron-up vote-arrow" :class="{ selected: course.quality_vote?.is_upvote }"
                    @click.stop="vote(course.id, 1, sort === 'best')"></i>
                  <div class="score">{{ sort === 'best' ? course.quality_score : course.difficulty_score }}</div>
                  <i class="fa-solid fa-chevron-down vote-arrow" :class="{ selected: course.quality_vote?.is_downvote }"
                    @click.stop="vote(course.id, -1, sort === 'best')"></i>
                </div>
              </div>

              <div class="course-info" @click="goToCourse(course.id)">
                <h3 class="course-title">
                  {{ course.course_code }}: {{ course.course_title }}
                </h3>

                <div class="course-meta">
                  <el-tag size="small" type="info" effect="plain">{{ course.review_count }} reviews</el-tag>

                  <template v-if="course.distribs.length">
                    <el-tag v-for="(distrib, index) in course.distribs" :key="index" size="small" class="distrib-tag">
                      {{ distrib.name }}
                    </el-tag>
                  </template>

                  <el-tag v-if="course.offered_times_string" size="small" type="success" effect="plain">
                    Offered during {{ course.offered_times_string }}
                  </el-tag>
                </div>

                <p v-if="course.short_description" class="course-description">
                  {{ course.short_description.length > 250 ?
                    course.short_description.substring(0, 250) + '...' :
                    course.short_description
                  }}
                  <span class="see-more">(see more)</span>
                </p>
              </div>
            </div>
          </el-card>

          <div class="pagination-container">
            <el-pagination layout="prev, pager, next" :total="totalPages * 10" :current-page="currentPage"
              @current-change="changePage" :disabled="loading" />
          </div>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();
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
    ElMessage.warning('You must be logged in to vote');
  }
};

const goToCourse = (courseId) => {
  router.push(`/course/${courseId}`);
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
  currentPage.value = 1; // Reset to first page when changing sort
  fetchCourses();
});
</script>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.course-card {
  margin-bottom: 20px;
}

.course-card-content {
  display: flex;
}

.score-column {
  margin-right: 20px;
  min-width: 80px;
}

.score-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.course-info {
  flex: 1;
  cursor: pointer;
}

.course-title {
  margin-top: 0;
  margin-bottom: 10px;
  color: var(--el-color-primary);
}

.course-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.distrib-tag {
  margin-right: 5px;
}

.course-description {
  color: #606266;
  margin-bottom: 0;
}

.see-more {
  color: var(--el-color-primary);
  cursor: pointer;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}

@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .course-card-content {
    flex-direction: column;
  }

  .score-column {
    margin-right: 0;
    margin-bottom: 15px;
  }

  .score-box {
    flex-direction: row;
    justify-content: center;
    gap: 15px;
  }
}
</style>
