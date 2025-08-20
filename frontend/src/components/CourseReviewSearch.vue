<template>
  <div class="course-review-search">
    <div v-if="loading" class="loading">Loading reviews...</div>
    <div v-else-if="error" class="error">Error: {{ error }}</div>
    <div v-else>
      <h1>
        {{ reviewsFullCount }}
        <router-link :to="`/course/${courseId}`">{{
          courseShortName
        }}</router-link>
        review results for "<span class="query">{{ query }}</span
        >"
      </h1>

      <form @submit.prevent="performSearch" class="course-review-search">
        <div class="form-group">
          <div class="input-group">
            <input
              name="q"
              type="text"
              class="form-control"
              placeholder="Review search..."
              v-model="searchQuery"
            />
            <span class="input-group-btn">
              <button type="submit" class="btn btn-default">Search</button>
            </span>
          </div>
        </div>
      </form>

      <div v-if="reviews.length === 0" class="alert alert-warning">
        <h3>
          Could not find any results. Please double-check your search query.
        </h3>
      </div>
      <table v-else class="table table-striped">
        <tbody>
          <tr v-for="review in reviews" :key="review.id">
            <td class="highlight-review">
              <b v-if="review.term">
                {{ review.term }}
                <b v-if="review.professor"> with {{ review.professor }}</b
                >:
              </b>
              <!-- Use MdPreview for displaying review comments in search results -->
              <MdPreview :model-value="review.comments" :sanitize="sanitize" />
            </td>
          </tr>
        </tbody>
      </table>

      <div
        v-if="!isAuthenticated && remaining > 0"
        class="col-md-12 text-center"
      >
        <h3>
          Please <router-link to="/accounts/login/">login</router-link> to see
          the remaining {{ remaining }} reviews for this search.
        </h3>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { MdPreview } from "md-editor-v3";
import "md-editor-v3/lib/style.css";
import DOMPurify from "dompurify";

const props = defineProps({
  courseId: {
    type: String,
    required: true,
  },
});

// Sanitize function using DOMPurify with enhanced security configuration
const sanitize = (html) =>
  DOMPurify.sanitize(html, {
    FORBID_TAGS: ["img", "svg", "math", "script", "iframe"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onmouseout"],
    USE_PROFILES: { html: true }, // Only allow HTML, no SVG or MathML
    SAFE_FOR_TEMPLATES: true, // Protect against template injection
    SANITIZE_DOM: true, // Protect against DOM clobbering
    KEEP_CONTENT: false, // Remove content of forbidden tags
  });

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
const isAuthenticated = ref(false);

const fetchReviews = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch(
      `/api/course/${props.courseId}/review_search/?q=${encodeURIComponent(searchQuery.value)}`,
    );
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
watch(
  () => route.query.q,
  (newQuery) => {
    if (newQuery !== searchQuery.value) {
      searchQuery.value = newQuery || "";
      fetchReviews();
    }
  },
  { immediate: true },
);

onMounted(async () => {
  searchQuery.value = route.query.q || "";
  await fetchReviews();
  await checkAuthentication();
});

const checkAuthentication = async () => {
  try {
    const response = await fetch("/api/user/status/");
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.value = data.isAuthenticated;
    } else {
      isAuthenticated.value = false;
    }
  } catch (e) {
    console.error("Error checking authentication:", e);
    isAuthenticated.value = false;
  }
};
</script>

<style scoped>
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
}

th {
  background-color: #f2f2f2;
  font-weight: bold;
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
