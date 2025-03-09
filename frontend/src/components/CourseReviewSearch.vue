<template>
  <div class="page-container">
    <el-skeleton :loading="loading" animated>
      <template #template>
        <div style="padding: 20px">
          <el-skeleton-item variant="h1" style="width: 50%" />
          <div style="margin-top: 20px">
            <el-skeleton-item variant="text" style="width: 100%" />
            <el-skeleton-item variant="text" style="width: 100%" />
            <el-skeleton-item variant="text" style="width: 100%" />
          </div>
        </div>
      </template>

      <template #default>
        <el-alert v-if="error" :title="error" type="error" show-icon />

        <div v-else class="review-search">
          <div class="review-search-header">
            <h1>
              {{ reviewsFullCount }}
              <router-link :to="`/course/${courseId}`">{{ courseShortName }}</router-link>
              review results for "<span class="query-text">{{ query }}</span>"
            </h1>

            <el-input v-model="searchQuery" placeholder="Review search..." class="search-input"
              @keyup.enter="performSearch">
              <template #append>
                <el-button @click="performSearch">
                  <i class="fa-solid fa-search"></i>
                </el-button>
              </template>
            </el-input>
          </div>

          <div v-if="reviews.length === 0" class="empty-state">
            <el-empty description="Could not find any results. Please double-check your search query." />
          </div>

          <div v-else class="reviews-list">
            <el-card v />
          </div>

          <div v-else class="reviews-list">
            <el-card v-for="review in reviews" :key="review.id" class="review-card">
              <template #header>
                <div class="review-header">
                  <span v-if="review.term">
                    <strong>{{ review.term }}</strong>
                    <span v-if="review.professor"> with <strong>{{ review.professor }}</strong></span>
                  </span>
                  <span v-else>Anonymous Review</span>
                </div>
              </template>
              <div class="review-content">{{ review.comments }}</div>
            </el-card>

            <div v-if="!isAuthenticated && remaining > 0" class="auth-message">
              <el-alert title="Want to see more reviews?" type="info" :closable="false" show-icon>
                <template #default>
                  <p>
                    Please <router-link to="/accounts/login/">login</router-link> to see the remaining {{ remaining }}
                    reviews
                    for this search.
                  </p>
                </template>
              </el-alert>
            </div>
          </div>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const props = defineProps({
  courseId: {
    type: String,
    required: true
  }
});

const route = useRoute();
const router = useRouter();
const searchQuery = ref('');
const reviews = ref([]);
const loading = ref(true);
const error = ref(null);
const reviewsFullCount = ref(0);
const remaining = ref(0);
const courseShortName = ref('');
const query = ref('');
const isAuthenticated = ref(false);

const fetchReviews = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch(`/api/course/${props.courseId}/review_search/?q=${encodeURIComponent(searchQuery.value)}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    reviews.value = data.reviews;
    reviewsFullCount.value = data.reviews_full_count;
    remaining.value = data.remaining;
    courseShortName.value = data.course_short_name;
    query.value = data.query; // Update the displayed query
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};

const performSearch = () => {
  router.push({ query: { q: searchQuery.value } }); // Update the query in the route
};

// Watch for changes in the route query
watch(() => route.query.q, (newQuery) => {
  if (newQuery !== searchQuery.value) {
    searchQuery.value = newQuery || '';
    fetchReviews();
  }
}, { immediate: true });

onMounted(async () => {
  searchQuery.value = route.query.q || '';
  await fetchReviews();
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
.review-search-header {
  margin-bottom: 30px;
}

.query-text {
  font-weight: bold;
  color: var(--el-color-primary);
}

.search-input {
  max-width: 500px;
  margin-top: 20px;
}

.empty-state {
  margin: 40px 0;
  display: flex;
  justify-content: center;
}

.reviews-list {
  margin-top: 20px;
}

.review-card {
  margin-bottom: 20px;
}

.review-header {
  display: flex;
  justify-content: space-between;
}

.review-content {
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
  white-space: pre-line;
}

.auth-message {
  margin: 30px 0;
}
</style>
