<template>
  <div class="course-review-search">
    <div v-if="loading" class="loading">Loading reviews...</div>
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <div v-if="!isAuthenticated" class="mt-4">
        <router-link
          to="/accounts/login/"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          Log In to Search Reviews
        </router-link>
      </div>
    </div>
    <div v-else>
      <h1 class="text-xl font-medium leading-6 text-gray-900 mb-6">
        {{ reviewsFullCount }}
        <router-link
          :to="`/course/${courseId}`"
          class="text-indigo-600 hover:text-indigo-800"
          >{{ courseShortName }}</router-link
        >
        review results for "<span class="query font-medium text-indigo-700">{{
          query
        }}</span
        >"
      </h1>

      <form @submit.prevent="performSearch" class="mb-6">
        <div class="flex max-w-md mx-auto">
          <div class="grid grid-cols-1 grow">
            <input
              name="q"
              type="search"
              class="col-start-1 row-start-1 block w-full rounded-l-md bg-white py-2 pr-3 pl-10 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
              placeholder="Search reviews..."
              v-model="searchQuery"
            />
            <MagnifyingGlassIcon
              class="pointer-events-none col-start-1 row-start-1 ml-3 size-5 self-center text-gray-400"
              aria-hidden="true"
            />
          </div>
          <button
            type="submit"
            class="flex shrink-0 items-center rounded-r-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600"
          >
            Search
          </button>
        </div>
      </form>

      <div v-if="reviews.length === 0" class="alert alert-warning">
        <h3>
          Could not find any results. Please double-check your search query.
        </h3>
      </div>
      <div v-else>
        <ReviewPagination
          :reviews="reviews"
          :isAuthenticated="isAuthenticated"
          :sanitize="sanitize"
          :maxLines="3"
          :pageSize="10"
          @reviewUpdated="updateReviewData"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { MagnifyingGlassIcon } from "@heroicons/vue/20/solid";
import "md-editor-v3/lib/style.css";
import { sanitize } from "../utils/sanitize";
import { useAuth } from "../composables/useAuth";
import ReviewPagination from "./ReviewPagination.vue";

const props = defineProps({
  courseId: {
    type: String,
    required: true,
  },
});

// sanitize imported from utils/sanitize.js

const route = useRoute();
const router = useRouter();
const searchQuery = ref("");
const reviews = ref([]);
const loading = ref(true);
const error = ref(null);
const reviewsFullCount = ref(0);
const remaining = ref(0);
const courseShortName = ref("");
const query = ref("");
const { isAuthenticated, checkAuthentication } = useAuth();

const fetchReviews = async () => {
  loading.value = true;
  error.value = null;

  // Check authentication before fetching reviews
  if (!isAuthenticated.value) {
    error.value = "Please log in to search reviews.";
    loading.value = false;
    return;
  }

  try {
    const response = await fetch(
      `/api/course/${props.courseId}/review_search/?q=${encodeURIComponent(searchQuery.value)}`,
    );
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        error.value =
          "Authentication required. Please log in to search reviews.";
        isAuthenticated.value = false;
      } else {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return;
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
watch(
  () => route.query.q,
  (newQuery) => {
    // Always update searchQuery and fetch when route changes
    searchQuery.value = newQuery || "";
    fetchReviews();
  },
  { immediate: true },
);

// Watch for authentication status changes
watch(isAuthenticated, (newAuth) => {
  if (newAuth) {
    // User just logged in, fetch reviews
    fetchReviews();
  }
});

onMounted(async () => {
  searchQuery.value = route.query.q || "";
  await checkAuthentication();
  await fetchReviews();
});

// authentication handled by useAuth composable

const updateReviewData = (updateData) => {
  const reviewIndex = reviews.value.findIndex(
    (r) => r.id === updateData.reviewId,
  );
  if (reviewIndex !== -1) {
    reviews.value[reviewIndex].kudos_count = updateData.kudos_count;
    reviews.value[reviewIndex].dislike_count = updateData.dislike_count;
    reviews.value[reviewIndex].user_vote = updateData.user_vote;
  }
};
</script>

<style scoped>
@import "../styles/MarkdownContent.css";

.course-review-search {
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

.alert-warning {
  color: #8a6d3b;
  background-color: #fcf8e3;
  border-color: #faebcc;
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid transparent;
  border-radius: 4px;
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

.btn-default {
  background-color: #f8f9fa;
  border-color: #ced4da;
  color: #343a40;
  border-radius: 0 4px 4px 0;
}
</style>
