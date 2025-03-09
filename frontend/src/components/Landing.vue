<template>
  <div class="landing-container">
    <el-card class="landing-card">
      <div class="landing-header">
        <img class="landing-logo" src="./placeholder.svg?height=100&width=100" alt="Logo">
        <h1>JI Course Review</h1>
        <h3>UMJI Course Reviews, Rankings, and Recommendations</h3>
        <p class="stats-text">
          {{ reviewCount.toLocaleString() }} reviews and counting
        </p>
      </div>

      <div class="landing-search">
        <el-input v-model="searchQuery" placeholder="Search for courses (e.g., ENGR101)" class="search-input"
          @keyup.enter="performSearch">
          <template #append>
            <el-button @click="performSearch" type="primary">
              <i class="fa-solid fa-search"></i> Search
            </el-button>
          </template>
        </el-input>
      </div>

      <div class="action-buttons">
        <el-button type="primary" @click="goToBestClasses" size="large">
          <i class="fa-solid fa-trophy"></i> Best Classes
        </el-button>
        <el-button type="success" @click="goToLayups" size="large">
          <i class="fa-solid fa-feather"></i>
          {{ isAuthenticated ? 'See Layups' : 'See Layups (requires login)' }}
        </el-button>
        <el-button type="info" @click="goToDepartments" size="large">
          <i class="fa-solid fa-building-columns"></i> Browse Departments
        </el-button>
      </div>

      <div class="contribute-section">
        <p>
          Know how to code?
          <a href="https://github.com/layuplist/layup-list" target="_blank">
            <i class="fa-brands fa-github"></i> Try contributing to Layup List!
          </a>
        </p>
      </div>
    </el-card>
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
    ElMessage({
      message: 'Search query must be at least 2 characters long',
      type: 'warning'
    });
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
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 120px);
  padding: 20px;
}

.landing-card {
  width: 100%;
  max-width: 800px;
}

.landing-header {
  text-align: center;
  margin-bottom: 30px;
}

.landing-logo {
  width: 100px;
  height: 100px;
  margin-bottom: 20px;
}

.stats-text {
  color: #909399;
  margin: 20px 0;
}

.landing-search {
  margin-bottom: 30px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 30px;
}

.contribute-section {
  text-align: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.contribute-section a {
  color: var(--el-color-primary);
  text-decoration: none;
}

.contribute-section a:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }

  .action-buttons .el-button {
    width: 100%;
  }
}
</style>
