<template>
  <div class="landing-container">
    <div class="row">
      <div class="col-md-12 text-center">
        <!-- <img class="landing-page-icon" src="/static/img/logo.svg" alt="Logo"> -->
        <h1>JI Course Review</h1>
        <h5>UMJI Course Reviews, Rankings, and Recommendations</h5>
        <p class="text-muted">
          {{ reviewCount.toLocaleString() }} reviews and counting<br />
        </p>
      </div>
    </div>
    <div class="row">
      <div class="col-md-6 col-md-offset-3 text-center">
        <div class="landing-search">
          <div class="form-group">
            <div class="input-group">
              <input v-model="searchQuery" type="text" class="search-input form-control"
                placeholder="Search for Courses...">
              <span class="input-group-btn">
                <button @click="performSearch" class="btn btn-default">Search</button>
              </span>
            </div>
          </div>
        </div>
        <button @click="goToBestClasses" class="btn btn-default">See Best Classes</button>
        <button v-if="isAuthenticated" @click="goToLayups" class="btn btn-default">See Layups</button>
        <button v-else @click="goToLayups" class="btn btn-default">See Layups (requires login)</button>
        <button @click="goToDepartments" class="btn btn-default">Browse</button>
        <br><br>
        <p> Know how to code? <a href="https://github.com/layuplist/layup-list">Try contributing to Layup List!</a> </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const reviewCount = ref(0);
const isAuthenticated = ref(false);
const searchQuery = ref('');

onMounted(async () => {
  await fetchLandingData();
  await checkAuthentication();
});

const fetchLandingData = async () => {
  try {
    const response = await fetch('/api/landing/');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    reviewCount.value = data.review_count;
  } catch (error) {
    console.error('Error fetching landing data:', error);
  }
};

const checkAuthentication = async () => {
  try {
    const response = await fetch('/api/user/status/');
    if (response.ok) {
      const data = await response.json();
      isAuthenticated.value = data.isAuthenticated;
    }
  } catch (error) {
    console.error('Error checking authentication:', error);
  }
};

const performSearch = () => {
  if (searchQuery.value.trim().length >= 2) {
    router.push({
      path: '/search',
      query: { q: searchQuery.value.trim() }
    });
  } else {
    alert('Search query must be at least 2 characters long');
  }
};

const goToBestClasses = () => {
  router.push('/best');
};

const goToLayups = () => {
  router.push('/layups');
};

const goToDepartments = () => {
  router.push('/departments');
};
</script>

<style scoped>
.landing-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.landing-page-icon {
  max-width: 100px;
  margin-bottom: 1rem;
}

.landing-search {
  max-width: 500px;
  margin: 1.5rem auto;
}

.btn {
  margin: 0.5rem;
}

.input-group {
  display: flex;
}

.form-control {
  flex: 1;
}
</style>
