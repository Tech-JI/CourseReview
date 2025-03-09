<template>
  <div class="page-container">
    <div v-if="loading" class="loading">
      <el-skeleton :rows="10" animated />
    </div>
    <div v-else-if="error" class="error">
      <el-alert :title="error" type="error" show-icon />
    </div>
    <div v-else class="departments-container">
      <h1>Departments</h1>

      <el-table :data="departments" style="width: 100%" @row-click="goToDepartment">
        <el-table-column prop="code" label="Code" width="120">
          <template #default="scope">
            <router-link :to="{ path: '/search', query: { q: scope.row.code } }">
              {{ scope.row.code }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="Department Name">
          <template #default="scope">
            <router-link v-if="scope.row.name" :to="{ path: '/search', query: { q: scope.row.code } }">
              {{ scope.row.name }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column prop="count" label="Courses" width="120" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
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

const goToDepartment = (row) => {
  router.push({ path: '/search', query: { q: row.code } });
};
</script>

<style scoped>
.loading,
.error {
  margin: 2em;
}

.departments-container {
  width: 100%;
}

.el-table {
  margin-top: 20px;
}

.el-table :deep(tbody tr) {
  cursor: pointer;
}

.el-table :deep(tbody tr:hover) {
  background-color: #f5f7fa;
}

a {
  color: var(--el-color-primary);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>
