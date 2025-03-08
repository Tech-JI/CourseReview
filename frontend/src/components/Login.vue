<template>
  <div class="login-container">
    <div class="row">
      <div class="col-md-12 text-center">
        <h1>Login</h1>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger">
      {{ error }}
    </div>

    <div class="row">
      <div class="col-md-4 col-md-offset-4">
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="email">Email</label>
            <input type="text" class="form-control" id="email" v-model="email" required placeholder="Enter your email">
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <input type="password" class="form-control" id="password" v-model="password" required
              placeholder="Enter your password">
          </div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            <span v-if="loading">Logging in...</span>
            <span v-else>Login</span>
          </button>
        </form>

        <div class="text-center mt-3">
          <p>
            Don't have an account?
            <router-link to="/accounts/signup">Sign up here</router-link>
          </p>
          <p>
            <router-link to="/accounts/password/reset">Forgot password?</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';

const router = useRouter();
const route = useRoute();
const email = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

const handleLogin = async () => {
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
        email: email.value,
        password: password.value,
        next: route.query.next || '/layups'
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }

    // Redirect to next URL or default
    router.push(data.next || '/layups');

  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
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
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.alert-danger {
  color: #721c24;
  background-color: #f8d7da;
  border-color: #f5c6cb;
  padding: 0.75rem 1.25rem;
  margin-bottom: 1rem;
  border: 1px solid transparent;
  border-radius: 0.25rem;
}

.form-group {
  margin-bottom: 1rem;
}

.btn-block {
  width: 100%;
}

.text-center {
  text-align: center;
}

.mt-3 {
  margin-top: 1rem;
}
</style>
