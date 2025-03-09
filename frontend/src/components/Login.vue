<template>
  <div class="page-container">
    <div class="login-container">
      <el-card class="login-card">
        <template #header>
          <div class="login-header">
            <h2>Login to JI Course Review</h2>
          </div>
        </template>

        <el-alert v-if="error" :title="error" type="error" show-icon class="login-error" />

        <el-form ref="loginForm" :model="formData" :rules="rules" label-position="top" @submit.prevent="handleLogin">
          <el-form-item label="Email" prop="email">
            <el-input v-model="formData.email" placeholder="Enter your email" prefix-icon="Message">
              <template #prefix>
                <i class="fa-solid fa-envelope"></i>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="Password" prop="password">
            <el-input v-model="formData.password" type="password" placeholder="Enter your password" show-password>
              <template #prefix>
                <i class="fa-solid fa-lock"></i>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" native-type="submit" :loading="loading" class="login-button">
              {{ loading ? 'Logging in...' : 'Login' }}
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-footer">
          <p>Don't have an account? <router-link to="/accounts/signup">Sign up here</router-link></p>
          <p><router-link to="/accounts/password/reset">Forgot password?</router-link></p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const loginForm = ref(null);
const error = ref('');
const loading = ref(false);

const formData = reactive({
  email: '',
  password: ''
});

const rules = {
  email: [
    { required: true, message: 'Please enter your email', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ]
};

const handleLogin = async () => {
  if (!loginForm.value) return;

  await loginForm.value.validate(async (valid) => {
    if (!valid) return;

    error.value = '';
    loading.value = true;

    try {
      const response = await fetch('/api/accounts/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          next: route.query.next || '/layups'
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }

      // Show success message
      ElMessage({
        message: 'Login successful!',
        type: 'success',
      });

      // Redirect to next URL or default
      router.push(data.next || '/layups');

    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  });
};

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 450px;
  transition: all 0.3s ease;
}

.login-card:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.login-header {
  text-align: center;
}

.login-header h2 {
  margin: 0;
  color: var(--el-color-primary);
  font-weight: 600;
}

.login-error {
  margin-bottom: 20px;
}

.login-button {
  width: 100%;
  height: 40px;
  font-size: 16px;
}

.login-footer {
  margin-top: 20px;
  text-align: center;
  color: #606266;
}

.login-footer a {
  color: var(--el-color-primary);
  text-decoration: none;
  transition: color 0.2s;
}

.login-footer a:hover {
  text-decoration: underline;
  color: var(--el-color-primary-dark-2);
}

@media (max-width: 768px) {
  .login-card {
    max-width: 100%;
  }
}
</style>
