<template>
  <div v-if="loading" class="loading">Loading...</div>
  <div v-else-if="error" class="error">Error: {{ error }}</div>
  <div v-else class="course-detail">
    <h1>{{ course.course_code }} | {{ course.course_title }}</h1>
    <h4 v-if="course.courseoffering_set.length > 0">Offered {{ currentTerm }} ({{ course.courseoffering_set[0].period
    }})</h4>
    <h4 v-else-if="course.last_offered">Last offered {{ course.last_offered }}</h4>
    <p v-if="course.description">{{ course.description }}</p>

    <div v-if="course.course_topics && course.course_topics.length > 0">
      <h3>Course Topics</h3>
      <ul>
        <li v-for="(topic, index) in course.course_topics" :key="index">
          {{ topic }}
        </li>
      </ul>
    </div>

    <p v-if="course.xlist && course.xlist.length > 0">
      Crosslisted with
      <span v-for="x in course.xlist" :key="x.id">
        <router-link :to="`/course/${x.id}`">{{ x.short_name }}</router-link>
      </span>
    </p>

    <div class="row">
      <div class="col-md-2 col-md-offset-2 text-center score-box">
        <template v-if="isAuthenticated">
          <span class="vote-arrow glyphicon glyphicon-chevron-up" :class="{
            selected: course.quality_vote && course.quality_vote.is_upvote,
            unselected: !course.quality_vote || !course.quality_vote.is_upvote,
          }" @click="vote(1, false)"></span>
          <h2 class="score">{{ course.quality_score }}</h2>
          <span class="vote-arrow glyphicon glyphicon-chevron-down" :class="{
            selected: course.quality_vote && course.quality_vote.is_downvote,
            unselected: !course.quality_vote || !course.quality_vote.is_downvote,
          }" @click="vote(-1, false)"></span>
          <p>said it was good</p>
        </template>
        <template v-else>
          <p><router-link to="/accounts/login/">Login</router-link> to see quality score</p>
        </template>
      </div>
      <div class="col-md-2 col-md-offset-4 text-center score-box">
        <template v-if="isAuthenticated">
          <span class="vote-arrow glyphicon glyphicon-chevron-up" :class="{
            selected: course.difficulty_vote && course.difficulty_vote.is_upvote,
            unselected: !course.difficulty_vote || !course.difficulty_vote.is_upvote,
          }" @click="vote(1, true)"></span>
          <h2 class="score">{{ course.difficulty_score }}</h2>
          <span class="vote-arrow glyphicon glyphicon-chevron-down" :class="{
            selected: course.difficulty_vote && course.difficulty_vote.is_downvote,
            unselected: !course.difficulty_vote || !course.difficulty_vote.is_downvote,
          }" @click="vote(-1, true)"></span>
          <p>called it a layup</p>
        </template>
        <template v-else>
          <p><router-link to="/accounts/login/">Login</router-link> to see difficulty score</p>
        </template>
      </div>
    </div>

    <div v-if="course.instructors && course.instructors.length > 0">
      <h3>Instructors</h3>
      <div class="instructor-list">
        <span v-for="(instructor, index) in course.instructors" :key="index" class="instructor-tag">
          {{ instructor }}
        </span>
      </div>
    </div>

    <div v-if="course.professors_and_review_count">
      <h3>Professors with Reviews</h3>
      <table class="table table-striped">
        <thead>
          <tr>
            <th>Name</th>
            <th>Reviews</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in course.professors_and_review_count" :key="item[0]">
            <td><router-link :to="`/course/${courseId}/review_search?q=${encodeURIComponent(item[0])}`">{{ item[0]
            }}</router-link></td>
            <td>{{ item[1] }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="isAuthenticated && course.review_set && course.review_set.length > 0">
      <h3>Reviews ({{ course.review_count }})</h3>
      <table class="table table-striped">
        <tbody>
          <tr v-for="review in course.review_set" :key="review.id">
            <td>
              <b v-if="review.term">{{ review.term }} <b v-if="review.professor"> with {{ review.professor }}</b>:
              </b>
              {{ review.comments }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="course.review_count > 0" class="auth-message">
      <p><router-link to="/accounts/signup/">Signup</router-link> or <router-link
          to="/accounts/login/">Login</router-link>
        to view all of the {{
          course.review_count }} reviews for this class.</p>
    </div>

    <div v-if="course.can_write_review">
      <h3>Write a Review for {{ course.course_code }}</h3>
      <form @submit.prevent="submitReview">
        <div>
          <label for="term">Term:</label>
          <input type="text" id="term" v-model="newReview.term" required :placeholder="currentTerm" />
        </div>
        <div>
          <label for="professor">Professor:</label>
          <input type="text" id="professor" v-model="newReview.professor" required
            placeholder="Full name, e.g., John Smith" />
        </div>
        <div>
          <label for="comments">Review:</label>
          <textarea id="comments" v-model="newReview.comments" required></textarea>
        </div>
        <button type="submit">Submit</button>
      </form>
    </div>

    <div v-else>
      <p v-if="isAuthenticated">Thanks for writing a review of this course!</p>
      <p v-else><router-link to="/accounts/login/">Login</router-link> to write a review.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";

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
      const errorData = await response.json();
      throw new Error(`HTTP error! status: ${response.status}, detail: ${JSON.stringify(errorData)}`);
    }
    course.value = await response.json();
    newReview.value = { term: "", professor: "", comments: "" };
    alert("Review submitted successfully!");
  } catch (error) {
    console.error("Error submitting review:", error);
    alert(`Error submitting review: ${error.message}`);
  }
};
</script>

<style scoped>
/* Add scoped styles here */
.loading,
.error {
  text-align: center;
  margin: 2em;
}

.vote-arrow {
  cursor: pointer;
}

.score-box {
  text-align: center;
  border: 1px solid #ddd;
  padding: 10px;
  margin-bottom: 20px;
}

.selected {
  color: green;
}

.unselected {
  color: gray;
}

.auth-message {
  background-color: #f8f9fa;
  border: 1px solid #ddd;
  padding: 15px;
  margin: 20px 0;
  border-radius: 5px;
  text-align: center;
}

.instructor-list {
  margin: 10px 0 20px 0;
}

.instructor-tag {
  display: inline-block;
  background-color: #e9ecef;
  color: #495057;
  padding: 5px 10px;
  margin: 0 5px 5px 0;
  border-radius: 15px;
  font-size: 0.9em;
}
</style>
