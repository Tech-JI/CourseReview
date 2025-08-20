<template>
  <div class="min-h-full">
    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center min-h-96">
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
        Loading course details...
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div class="rounded-md bg-red-50 p-4">
        <div class="flex">
          <ExclamationTriangleIcon
            class="h-5 w-5 text-red-400"
            aria-hidden="true"
          />
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">
              Error loading course
            </h3>
            <div class="mt-2 text-sm text-red-700">{{ error }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Course Content -->
    <div v-else class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <!-- Course Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">
          {{ course.course_code }} | {{ course.course_title }}
        </h1>
        <div class="mt-2 flex items-center space-x-4">
          <span
            v-if="course.courseoffering_set.length > 0"
            class="inline-flex items-center rounded-full bg-green-100 px-3 py-0.5 text-sm font-medium text-green-800"
          >
            Offered {{ currentTerm }} ({{
              course.courseoffering_set[0].period
            }})
          </span>
          <span
            v-else-if="course.last_offered"
            class="inline-flex items-center rounded-full bg-yellow-100 px-3 py-0.5 text-sm font-medium text-yellow-800"
          >
            Last offered {{ course.last_offered }}
          </span>
        </div>
        <p
          v-if="course.description"
          class="mt-4 text-lg text-gray-600 max-w-3xl"
        >
          {{ course.description }}
        </p>
      </div>

      <!-- Course Info Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        <!-- Left Column: Course Topics and Cross-listings -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Course Topics -->
          <div
            v-if="course.course_topics && course.course_topics.length > 0"
            class="bg-white overflow-hidden shadow sm:rounded-lg"
          >
            <div class="px-4 py-5 sm:p-6">
              <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                Course Topics
              </h3>
              <ul class="space-y-2">
                <li
                  v-for="(topic, index) in course.course_topics"
                  :key="index"
                  class="flex items-start"
                >
                  <CheckIcon
                    class="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0"
                  />
                  <span class="text-sm text-gray-700">{{ topic }}</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Cross-listed Courses -->
          <div
            v-if="course.xlist && course.xlist.length > 0"
            class="bg-white overflow-hidden shadow sm:rounded-lg"
          >
            <div class="px-4 py-5 sm:p-6">
              <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
                Cross-listed with
              </h3>
              <div class="flex flex-wrap gap-2">
                <router-link
                  v-for="x in course.xlist"
                  :key="x.id"
                  :to="`/course/${x.id}`"
                  class="inline-flex items-center rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-700/10 hover:bg-indigo-100"
                >
                  {{ x.short_name }}
                </router-link>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Voting Cards -->
        <div class="space-y-6">
          <!-- Quality Score Card -->
          <div class="bg-white overflow-hidden shadow sm:rounded-lg">
            <div class="px-4 py-5 sm:p-6 text-center">
              <h3 class="text-lg font-medium text-gray-900 mb-4">
                Quality Score
              </h3>
              <template v-if="isAuthenticated">
                <div class="space-y-4">
                  <div class="flex items-center justify-center gap-2 mb-2">
                    <span class="text-3xl font-bold text-indigo-600">
                      {{
                        course.quality_score > 0
                          ? course.quality_score.toFixed(1)
                          : "N/A"
                      }}
                    </span>
                    <span class="text-xs text-gray-500">
                      ({{ course.quality_vote_count ?? 0 }} ratings)
                    </span>
                  </div>
                  <div class="text-sm text-gray-500 mb-4">
                    Rate this course (1-5 stars)
                  </div>
                  <div class="flex justify-center space-x-1">
                    <button
                      v-for="star in 5"
                      :key="star"
                      @click="vote(star, false)"
                      :class="[
                        'p-1 rounded transition-colors',
                        course.quality_vote && course.quality_vote.value >= star
                          ? 'text-yellow-500 hover:text-yellow-600'
                          : 'text-gray-300 hover:text-yellow-400',
                      ]"
                    >
                      <svg class="h-6 w-6 fill-current" viewBox="0 0 24 24">
                        <path
                          d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                        />
                      </svg>
                    </button>
                  </div>
                  <div class="text-xs text-gray-500">
                    Your rating:
                    {{
                      course.quality_vote
                        ? course.quality_vote.value
                        : "Not rated"
                    }}
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="text-center py-4">
                  <LockClosedIcon class="mx-auto h-12 w-12 text-gray-400" />
                  <p class="mt-2 text-sm text-gray-500">
                    <router-link
                      to="/accounts/login/"
                      class="font-medium text-indigo-600 hover:text-indigo-500"
                    >
                      Login
                    </router-link>
                    to see quality score
                  </p>
                </div>
              </template>
            </div>
          </div>

          <!-- Difficulty Score Card -->
          <div class="bg-white overflow-hidden shadow sm:rounded-lg">
            <div class="px-4 py-5 sm:p-6 text-center">
              <h3 class="text-lg font-medium text-gray-900 mb-4">
                Difficulty Score
              </h3>
              <template v-if="isAuthenticated">
                <div class="space-y-4">
                  <div class="flex items-center justify-center gap-2 mb-2">
                    <span class="text-3xl font-bold text-green-600">
                      {{
                        course.difficulty_score > 0
                          ? course.difficulty_score.toFixed(1)
                          : "N/A"
                      }}
                    </span>
                    <span class="text-xs text-gray-500">
                      ({{ course.difficulty_vote_count ?? 0 }} ratings)
                    </span>
                  </div>
                  <div class="text-sm text-gray-500 mb-4">
                    Rate difficulty (1=Very Easy, 5=Very Hard)
                  </div>
                  <div class="flex justify-center space-x-1">
                    <button
                      v-for="star in 5"
                      :key="star"
                      @click="vote(star, true)"
                      :class="[
                        'p-1 rounded transition-colors',
                        course.difficulty_vote &&
                        course.difficulty_vote.value >= star
                          ? 'text-red-500 hover:text-red-600'
                          : 'text-gray-300 hover:text-red-400',
                      ]"
                    >
                      <svg class="h-6 w-6 fill-current" viewBox="0 0 24 24">
                        <path
                          d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
                        />
                      </svg>
                    </button>
                  </div>
                  <div class="text-xs text-gray-500">
                    Your rating:
                    {{
                      course.difficulty_vote
                        ? course.difficulty_vote.value
                        : "Not rated"
                    }}
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="text-center py-4">
                  <LockClosedIcon class="mx-auto h-12 w-12 text-gray-400" />
                  <p class="mt-2 text-sm text-gray-500">
                    <router-link
                      to="/accounts/login/"
                      class="font-medium text-indigo-600 hover:text-indigo-500"
                    >
                      Login
                    </router-link>
                    to see difficulty score
                  </p>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Instructors Section -->
      <div
        v-if="course.instructors && course.instructors.length > 0"
        class="mb-8"
      >
        <div class="bg-white overflow-hidden shadow sm:rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
              Instructors
            </h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="(instructor, index) in course.instructors"
                :key="index"
                class="inline-flex items-center rounded-full bg-gray-50 px-3 py-1 text-sm font-medium text-gray-700"
              >
                <UsersIcon class="h-4 w-4 mr-1" />
                {{ instructor }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Professors with Reviews -->
      <div v-if="course.professors_and_review_count" class="mb-8">
        <div class="bg-white overflow-hidden shadow sm:rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
              Professors with Reviews
            </h3>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Name
                    </th>
                    <th
                      scope="col"
                      class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                    >
                      Reviews
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  <tr
                    v-for="item in course.professors_and_review_count"
                    :key="item[0]"
                    class="hover:bg-gray-50"
                  >
                    <td class="px-6 py-4 whitespace-nowrap">
                      <router-link
                        :to="`/course/${courseId}/review_search?q=${encodeURIComponent(item[0])}`"
                        class="text-indigo-600 hover:text-indigo-900 font-medium"
                      >
                        {{ item[0] }}
                      </router-link>
                    </td>
                    <td
                      class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                    >
                      <span
                        class="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
                      >
                        {{ item[1] }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- Reviews Section -->
      <div
        v-if="
          isAuthenticated && course.review_set && course.review_set.length > 0
        "
        class="mb-8"
      >
        <div class="bg-white overflow-hidden shadow sm:rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg font-medium leading-6 text-gray-900 mb-6">
              Reviews ({{ course.review_count }})
            </h3>
            <div class="space-y-4">
              <div
                v-for="review in course.review_set"
                :key="review.id"
                class="border-l-4 border-indigo-400 bg-indigo-50 p-4"
              >
                <div class="flex">
                  <div class="ml-3">
                    <div
                      v-if="review.term"
                      class="text-sm font-medium text-indigo-800"
                    >
                      {{ review.term }}
                      <span v-if="review.professor">
                        with {{ review.professor }}</span
                      >
                    </div>
                    <!-- Use MdPreview for displaying review comments -->
                    <MdPreview
                      :model-value="review.comments"
                      :sanitize="sanitize"
                      class="mt-2 text-sm text-indigo-700 markdown-content"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- Auth message for reviews -->
      <div v-else-if="course.review_count > 0" class="mb-8">
        <div class="rounded-md bg-blue-50 p-4">
          <div class="flex">
            <InformationCircleIcon
              class="h-5 w-5 text-blue-400"
              aria-hidden="true"
            />
            <div class="ml-3">
              <h3 class="text-sm font-medium text-blue-800">
                {{ course.review_count }} reviews available
              </h3>
              <div class="mt-2 text-sm text-blue-700">
                <router-link
                  to="/accounts/signup/"
                  class="font-medium underline hover:text-blue-600"
                >
                  Sign up
                </router-link>
                or
                <router-link
                  to="/accounts/login/"
                  class="font-medium underline hover:text-blue-600"
                >
                  log in
                </router-link>
                to view all reviews for this class.
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Write Review Section -->
      <div v-if="course.can_write_review" class="mb-8">
        <div class="bg-white overflow-hidden shadow sm:rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg font-medium leading-6 text-gray-900 mb-6">
              Write a Review for {{ course.course_code }}
            </h3>
            <form @submit.prevent="submitReview" class="space-y-6">
              <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label
                    for="term"
                    class="block text-sm font-medium leading-6 text-gray-900"
                  >
                    Term
                  </label>
                  <input
                    type="text"
                    id="term"
                    v-model="newReview.term"
                    required
                    :placeholder="currentTerm"
                    class="mt-1 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  />
                </div>
                <div>
                  <label
                    for="professor"
                    class="block text-sm font-medium leading-6 text-gray-900"
                  >
                    Professor
                  </label>
                  <input
                    type="text"
                    id="professor"
                    v-model="newReview.professor"
                    required
                    placeholder="Full name, e.g., John Smith"
                    class="mt-1 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  />
                </div>
              </div>
              <div>
                <label
                  id="review-comments-label"
                  class="block text-sm font-medium leading-6 text-gray-900"
                >
                  Review
                </label>
                <MdEditor
                  id="review-comments"
                  v-model="newReview.comments"
                  :sanitize="sanitize"
                  :toolbars="[
                    'bold',
                    'italic',
                    'strikeThrough',
                    'title',
                    'sub',
                    'sup',
                    'quote',
                    'unorderedList',
                    'orderedList',
                    'task',
                    'codeRow',
                    'code',
                    'link',
                    'table',
                    'katex',
                    'revoke',
                    'next',
                    'preview',
                    'htmlPreview',
                  ]"
                  aria-labelledby="review-comments-label"
                  role="textbox"
                  tabindex="0"
                  style="height: 300px"
                  class="mt-1 block w-full rounded-md border-0 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 markdown-content"
                />
              </div>
              <div class="flex justify-end">
                <button
                  type="submit"
                  class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                >
                  Submit Review
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Review Status Message -->
      <div v-else class="mb-8">
        <div class="rounded-md bg-gray-50 p-4">
          <div class="text-center">
            <p v-if="isAuthenticated" class="text-sm text-gray-600">
              Thanks for writing a review of this course!
            </p>
            <p v-else class="text-sm text-gray-600">
              <router-link
                to="/accounts/login/"
                class="font-medium text-indigo-600 hover:text-indigo-500"
              >
                Login
              </router-link>
              to write a review.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ExclamationTriangleIcon,
  CheckIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  LockClosedIcon,
  UsersIcon,
  InformationCircleIcon,
} from "@heroicons/vue/24/outline";
import { MdEditor, MdPreview } from "md-editor-v3";
import "md-editor-v3/lib/style.css";
import DOMPurify from "dompurify";

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
    if (confirm("Please login to vote!")) {
      router.push("/accounts/login");
    }
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
        };
      }
      if (typeof data.new_vote_count !== "undefined") {
        course.value.difficulty_vote_count = data.new_vote_count;
      }
    } else {
      course.value.quality_score = data.new_score;
      if (data.was_unvote) {
        course.value.quality_vote = null;
      } else {
        course.value.quality_vote = {
          value: value,
        };
      }
      if (typeof data.new_vote_count !== "undefined") {
        course.value.quality_vote_count = data.new_vote_count;
      }
    }
    // Update new_vote_count if present in response
  } catch (e) {
    console.error("Error voting:", e);
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

const submitReview = async () => {
  if (!isAuthenticated.value) {
    alert("You must be logged in to submit a review.");
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
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorData = await response.json();
        // Handle Django REST Framework serializer errors (which are objects with field arrays)
        if (
          errorData &&
          typeof errorData === "object" &&
          !Array.isArray(errorData)
        ) {
          const errorLines = [];
          for (const [field, messages] of Object.entries(errorData)) {
            if (Array.isArray(messages) && messages.length > 0) {
              // Join multiple messages for a single field with a space
              errorLines.push(`${field}: ${messages.join(" ")}`);
            } else if (typeof messages === "string") {
              errorLines.push(`${field}: ${messages}`);
            }
          }
          if (errorLines.length > 0) {
            errorMessage = errorLines.join("\n"); // Join fields with a newline
          } else {
            // Fallback if structure is not as expected
            errorMessage = JSON.stringify(errorData);
          }
        } else if (errorData.detail) {
          // Handle generic DRF error responses
          errorMessage = errorData.detail;
        } else if (typeof errorData === "string") {
          errorMessage = errorData;
        } else {
          // Fallback for other object types or arrays
          errorMessage = JSON.stringify(errorData);
        }
      } catch (e) {
        // If parsing JSON fails, use the status text
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }
    course.value = await response.json();
    newReview.value = { term: "", professor: "", comments: "" };
    alert("Review submitted successfully!");
  } catch (error) {
    console.error("Error submitting review:", error);
    // Use alert with newline characters preserved
    alert(`Error submitting review:\n${error.message}`);
  }
};
</script>

<style scoped>
/* Restore list styling for markdown content */
:deep(.markdown-content) ul {
  list-style-type: disc;
  padding-left: 1.5rem;
}

:deep(.markdown-content) ol {
  list-style-type: decimal;
  padding-left: 1.5rem;
}

:deep(.markdown-content) ul ul,
:deep(.markdown-content) ol ul {
  list-style-type: circle;
}

:deep(.markdown-content) ul ol,
:deep(.markdown-content) ol ol {
  list-style-type: lower-alpha;
}
</style>
