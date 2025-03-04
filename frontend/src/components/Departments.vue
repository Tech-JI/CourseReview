<template>
  <div v-if="loading" class="loading">Loading departments...</div>
  <div v-else-if="error" class="error">Error: {{ error }}</div>
  <div v-else class="departments-container">
    <h1>Departments</h1>
    <table class="table table-hover">
      <thead>
        <tr>
          <th>Code</th>
          <th>Department Name</th>
          <th>Courses</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="dept in departments" :key="dept.code" @click="goToDepartment(dept.code)" role="button">
          <td><a>{{ dept.code }}</a></td>
          <td><a v-if="dept.name">{{ dept.name }}</a></td>
          <td>{{ dept.count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const departments = ref([]);
const loading = ref(true);
const error = ref(null);

onMounted(async () => {
  await fetchDepartments();
});

const fetchDepartments = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await fetch('/api/departments/');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    departments.value = await response.json();
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};

import { useRouter } from 'vue-router';
const router = useRouter();

const goToDepartment = (code) => {
  router.push({ path: '/search', query: { q: code } });
};
</script>

<style scoped>
.loading,
.error {
  text-align: center;
  margin: 2em;
}

.departments-container {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
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
  cursor: pointer;
}

th {
  background-color: #f2f2f2;
  font-weight: bold;
}
</style>
