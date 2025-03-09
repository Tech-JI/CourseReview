<template>
  <div class="page-container">
    <el-skeleton :loading="loading" animated>
      <template #template>
        <div style="padding: 20px">
          <el-skeleton-item variant="h1" style="width: 50%" />
          <el-skeleton-item variant="text" style="margin-top: 16px; width: 80%" />
          <el-skeleton-item variant="text" style="margin-top: 16px; width: 60%" />
          <el-skeleton-item variant="text" style="margin-top: 16px; width: 70%" />
        </div>
      </template>

      <template #default>
        <el-alert v-if="error" :title="error" type="error" show-icon />

        <div v-else class="course-detail">
          <div class="course-header">
            <h1>{{ course.course_code }} | {{ course.course_title }}</h1>
            <h4 v-if="course.courseoffering_set?.length > 0">
              Offered {{ currentTerm }} ({{ course.courseoffering_set[0].period }})
            </h4>
            <h4 v-else-if="course.last_offered">Last offered {{ course.last_offered }}</h4>
          </div>

          <el-divider />

          <el-descriptions :column="1" border>
            <el-descriptions-item v-if="course.description" label="Description">
              {{ course.description }}
            </el-descriptions-item>

            <el-descriptions-item v-if="course.course_topics?.length > 0" label="Course Topics">
              <el-tag v-for="(topic, index) in course.course_topics" :key="index" class="topic-tag">
                {{ topic }}
              </el-tag>
            </el-descriptions-item>

            <el-descriptions-item v-if="course.xlist?.length > 0" label="Crosslisted with">
              <router-link v-for="x in course.xlist" :key="x.id" :to="`/course/${x.id}`" class="crosslist-link">
                {{ x.short_name }}
              </router-link>
            </el-descriptions-item>
          </el-descriptions>

          <div class="score-section">
            <el-row :gutter="20">
              <el-col :xs="24" :sm="12">
                <el-card class="score-card">
                  <template #header>
                    <div class="score-header">Quality Score</div>
                  </template>

                  <template v-if="isAuthenticated">
                    <div class="score-content">
                      <i class="fa-solid fa-chevron-up vote-arrow" :class="{ selected: course.quality_vote?.is_upvote }"
                        @click="vote(1, false)"></i>
                      <div class="score">{{ course.quality_score }}</div>
                      <i class="fa-solid fa-chevron-down vote-arrow"
                        :class="{ selected: course.quality_vote?.is_downvote }" @click="vote(-1, false)"></i>
                    </div>
                    <div class="score-label">said it was good</div>
                  </template>
                  <template v-else>
                    <div class="auth-prompt">
                      <router-link to="/accounts/login/">Login</router-link> to see quality score
                    </div>
                  </template>
                </el-card>
              </el-col>

              <el-col :xs="24" :sm="12">
                <el-card class="score-card">
                  <template #header>
                    <div class="score-header">Layup Score</div>
                  </template>

                  <template v-if="isAuthenticated">
                    <div class="score-content">
                      <i class="fa-solid fa-chevron-up vote-arrow"
                        :class="{ selected: course.difficulty_vote?.is_upvote }" @click="vote(1, true)"></i>
                      <div class="score">{{ course.difficulty_score }}</div>
                      <i class="fa-solid fa-chevron-down vote-arrow"
                        :class="{ selected: course.difficulty_vote?.is_downvote }" @click="vote(-1, true)"></i>
                    </div>
                    <div class="score-label">called it a layup</div>
                  </template>
                  <template v-else>
                    <div class="auth-prompt">
                      <router-link to="/accounts/login/">Login</router-link> to see layup score
                    </div>
                  </template>
                </el-card>
              </el-col>
            </el-row>
          </div>

          <div v-if="course.instructors?.length > 0" class="instructors-section">
            <h3>Instructors</h3>
            <div class="instructor-list">
              <el-tag v-for="(instructor, index) in course.instructors" :key="index" class="instructor-tag" type="info"
                effect="plain">
                {{ instructor }}
              </el-tag>
            </div>
          </div>

          <div v-if="course.professors_and_review_count" class="professors-section">
            <h3>Professors with Reviews</h3>
            <el-table :data="course.professors_and_review_count" stripe style="width: 100%">
              <el-table-column label="Name" prop="0">
                <template #default="scope">
                  <router-link :to="`/course/${courseId}/review_search?q=${encodeURIComponent(scope.row[0])}`">
                    {{ scope.row[0] }}
                  </router-link>
                </template>
              </el-table-column>
              <el-table-column label="Reviews" prop="1" />
            </el-table>
          </div>

          <div v-if="isAuthenticated && course.review_set?.length > 0" class="reviews-section">
            <h3>Reviews ({{ course.review_count }})</h3>
            <el-collapse>
              <el-collapse-item v-for="(review, index) in course.review_set" :key="review.id" :name="index">
                <template #title>
                  <span v-if="review.term">
                    {{ review.term }}
                    <span v-if="review.professor">with {{ review.professor }}</span>
                  </span>
                  <span v-else>Anonymous Review</span>
                </template>
                <div class="review-content" v-html="renderMarkdown(review.comments)"></div>
              </el-collapse-item>
            </el-collapse>
          </div>
          <div v-else-if="course.review_count > 0" class="auth-message">
            <el-alert title="Want to see all reviews?" type="info" :closable="false" show-icon>
              <template #default>
                <p>
                  <router-link to="/accounts/signup/">Signup</router-link> or
                  <router-link to="/accounts/login/">Login</router-link>
                  to view all of the {{ course.review_count }} reviews for this class.
                </p>
              </template>
            </el-alert>
          </div>

          <div v-if="course.can_write_review" class="write-review-section">
            <h3>Write a Review for {{ course.course_code }}</h3>
            <el-form @submit.prevent="submitReview" label-position="top">
              <el-form-item label="Term">
                <el-input v-model="newReview.term" placeholder="e.g., 25S" />
              </el-form-item>
              <el-form-item label="Professor">
                <el-autocomplete v-model="newReview.professor" :fetch-suggestions="queryProfessorSearch"
                  placeholder="Full name, e.g., John Smith" :trigger-on-focus="true" @select="handleProfessorSelect"
                  class="professor-autocomplete">
                  <template #default="{ item }">
                    <div class="professor-suggestion">
                      {{ item.value }}
                      <span v-if="item.isExact" class="exact-match">(exact match)</span>
                    </div>
                  </template>
                </el-autocomplete>
              </el-form-item>
              <el-form-item label="Review">
                <el-input v-model="newReview.comments" type="textarea" :rows="4"
                  placeholder="Share your experience with this course... (Markdown supported)" />
                <div class="markdown-hint">
                  <i class="fa-brands fa-markdown"></i> Markdown supported
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" native-type="submit">Submit Review</el-button>
              </el-form-item>
            </el-form>
          </div>
          <div v-else-if="isAuthenticated" class="review-message">
            <el-alert title="Thanks for writing a review of this course!" type="success" :closable="false" show-icon />
          </div>
          <div v-else class="review-message">
            <el-alert title="Want to share your experience?" type="info" :closable="false" show-icon>
              <template #default>
                <p><router-link to="/accounts/login/">Login</router-link> to write a review.</p>
              </template>
            </el-alert>
          </div>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const route = useRoute();
const router = useRouter();
const course = ref(null);
const loading = ref(true);
const error = ref(null);
const currentTerm = "25S";
const isAuthenticated = ref(false);
const newReview = ref({
  term: "",
  professor: "",
  comments: "",
});

const courseId = computed(() => {
  return route.params.course_id;
});

// Computed property to get all professor names from the course data
const professorNames = computed(() => {
  const names = new Set();

  // Add instructors
  if (course.value?.instructors) {
    course.value.instructors.forEach(name => names.add(name));
  }

  // Add professors with reviews
  if (course.value?.professors_and_review_count) {
    course.value.professors_and_review_count.forEach(item => names.add(item[0]));
  }

  // Add professors from reviews
  if (course.value?.review_set) {
    course.value.review_set.forEach(review => {
      if (review.professor) names.add(review.professor);
    });
  }

  return Array.from(names);
});

// Function to search for professor names
const queryProfessorSearch = (queryString, callback) => {
  const results = [];

  if (queryString) {
    const lowerQuery = queryString.toLowerCase();

    // Check for exact matches first
    const exactMatches = professorNames.value.filter(name =>
      name.toLowerCase() === lowerQuery
    );

    if (exactMatches.length > 0) {
      exactMatches.forEach(name => {
        results.push({
          value: name,
          isExact: true
        });
      });
    }

    // Then check for partial matches
    const partialMatches = professorNames.value.filter(name =>
      name.toLowerCase().includes(lowerQuery) &&
      !exactMatches.includes(name)
    );

    partialMatches.forEach(name => {
      results.push({
        value: name,
        isExact: false
      });
    });
  } else {
    // If no query, show all professors
    professorNames.value.forEach(name => {
      results.push({
        value: name,
        isExact: false
      });
    });
  }

  callback(results);
};

// Handle professor selection from autocomplete
const handleProfessorSelect = (item) => {
  newReview.value.professor = item.value;
};

// Function to render markdown safely
const renderMarkdown = (text) => {
  if (!text) return '';

  // Parse markdown to HTML
  const rawHtml = marked(text);

  // Sanitize HTML to prevent XSS attacks
  const cleanHtml = DOMPurify.sanitize(rawHtml);

  return cleanHtml;
};

onMounted(async () => {
  if (courseId.value) {
    await fetchCourse();
  }
  checkAuthentication();
});

const fetchCourse = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch(`/api/course/${courseId.value}/`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    course.value = await response.json();
  } catch (e) {
    error.value = e.message;
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
    } else {
      isAuthenticated.value = false;
    }
  } catch (e) {
    console.error("Error checking authentication:", e);
    isAuthenticated.value = false;
  }
};

const vote = async (value, forLayup) => {
  if (!isAuthenticated.value) {
    ElMessageBox.confirm('You need to be logged in to vote. Would you like to login now?', 'Login Required', {
      confirmButtonText: 'Go to Login',
      cancelButtonText: 'Cancel',
      type: 'info'
    }).then(() => {
      router.push("/accounts/login");
    }).catch(() => { });
    return;
  }

  try {
    const postData = { value, forLayup };
    const response = await fetch(`/api/course/${courseId.value}/vote`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(postData),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    if (forLayup) {
      course.value.difficulty_score = data.new_score;
      if (data.was_unvote) {
        course.value.difficulty_vote = null;
      } else {
        course.value.difficulty_vote = {
          value: value,
          is_upvote: value > 0,
          is_downvote: value < 0,
        };
      }
    } else {
      course.value.quality_score = data.new_score;
      if (data.was_unvote) {
        course.value.quality_vote = null;
      } else {
        course.value.quality_vote = {
          value: value,
          is_upvote: value > 0,
          is_downvote: value < 0,
        };
      }
    }
  } catch (e) {
    console.error("Error voting:", e);
    ElMessage.error("Failed to submit vote. Please try again.");
  }
};

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const submitReview = async () => {
  if (!isAuthenticated.value) {
    ElMessage.warning("You must be logged in to submit a review.");
    return;
  }

  if (!newReview.value.term || !newReview.value.professor || !newReview.value.comments) {
    ElMessage.warning("Please fill in all fields");
    return;
  }

  try {
    const response = await fetch(`/api/course/${courseId.value}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(newReview.value),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP error! status: ${response.status}, detail: ${JSON.stringify(errorData)}`);
    }

    course.value = await response.json();
    newReview.value = { term: "", professor: "", comments: "" };
    ElMessage.success("Review submitted successfully!");
  } catch (error) {
    console.error("Error submitting review:", error);
    ElMessage.error(`Error submitting review: ${error.message}`);
  }
};
</script>

<style scoped>
.course-header {
  margin-bottom: 20px;
}

.course-header h1 {
  margin-bottom: 10px;
  color: var(--el-color-primary);
}

.topic-tag {
  margin-right: 8px;
  margin-bottom: 8px;
}

.crosslist-link {
  margin-right: 10px;
  color: var(--el-color-primary);
  text-decoration: none;
}

.crosslist-link:hover {
  text-decoration: underline;
}

.score-section {
  margin: 30px 0;
}

.score-card {
  text-align: center;
  margin-bottom: 20px;
}

.score-header {
  font-weight: bold;
}

.score-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 10px 0;
}

.score-label {
  color: #909399;
  font-size: 14px;
}

.auth-prompt {
  padding: 20px 0;
  text-align: center;
}

.auth-prompt a {
  color: var(--el-color-primary);
  text-decoration: none;
}

.auth-prompt a:hover {
  text-decoration: underline;
}

.instructors-section,
.professors-section,
.reviews-section,
.write-review-section {
  margin-top: 30px;
}

.instructor-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.review-content {
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
}

.auth-message,
.review-message {
  margin: 30px 0;
}

.professor-autocomplete {
  width: 100%;
}

.professor-suggestion {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.exact-match {
  font-size: 12px;
  color: #67c23a;
  margin-left: 8px;
}

.markdown-hint {
  margin-top: 5px;
  font-size: 12px;
  color: #909399;
}

@media (max-width: 768px) {
  .course-header h1 {
    font-size: 1.5rem;
  }
}

/* Override scoped styles for markdown content */
:deep(.review-content) {
  line-height: 1.6;
}

:deep(.review-content h1),
:deep(.review-content h2),
:deep(.review-content h3),
:deep(.review-content h4),
:deep(.review-content h5),
:deep(.review-content h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
}

:deep(.review-content p) {
  margin-bottom: 1em;
}

:deep(.review-content ul),
:deep(.review-content ol) {
  padding-left: 2em;
  margin-bottom: 1em;
}

:deep(.review-content blockquote) {
  border-left: 4px solid #ddd;
  padding-left: 1em;
  color: #666;
  margin-left: 0;
  margin-right: 0;
}

:deep(.review-content code) {
  background-color: #f0f0f0;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: monospace;
}

:deep(.review-content pre) {
  background-color: #f0f0f0;
  padding: 1em;
  border-radius: 5px;
  overflow-x: auto;
}

:deep(.review-content a) {
  color: var(--el-color-primary);
  text-decoration: none;
}

:deep(.review-content a:hover) {
  text-decoration: underline;
}
</style>
