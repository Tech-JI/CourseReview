<template>
  <!--
    Improved login form using TailwindPlus design patterns
    Consistent with existing app design language
  -->
  <div
    class="flex min-h-full flex-1 flex-col justify-center py-12 sm:px-6 lg:px-8"
  >
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="text-center">
        <h2
          class="mt-6 text-center text-2xl/9 font-bold tracking-tight text-gray-900"
        >
          Sign in to your account
        </h2>
        <p class="mt-2 text-sm text-gray-600">
          Access your JI Course Review dashboard
        </p>
      </div>
    </div>

    <div class="mt-10 sm:mx-auto sm:w-full sm:max-w-[480px]">
      <div class="bg-white px-6 py-12 shadow-sm sm:rounded-lg sm:px-12">
        <!-- Login Method Tabs -->
        <div class="mb-8">
          <nav class="flex space-x-8" aria-label="Tabs">
            <button
              type="button"
              :class="[
                'whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors',
                !showQuestionnaireLogin
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              ]"
              @click="showQuestionnaireLogin = false"
            >
              Password Login
            </button>
            <button
              type="button"
              :class="[
                'whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors',
                showQuestionnaireLogin
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              ]"
              @click="showQuestionnaireLogin = true"
            >
              SJTU Authentication
            </button>
          </nav>
        </div>

        <!-- Error Alert -->
        <div v-if="error" class="rounded-md bg-red-50 p-4 mb-6">
          <div class="flex">
            <ExclamationTriangleIcon
              class="h-5 w-5 text-red-400 shrink-0"
              aria-hidden="true"
            />
            <div class="ml-3">
              <h3 class="text-sm font-medium text-red-800">Login failed</h3>
              <div class="mt-2 text-sm text-red-700">{{ error }}</div>
            </div>
          </div>
        </div>

        <!-- Password Login Form -->
        <form
          v-if="!showQuestionnaireLogin"
          class="space-y-6"
          @submit.prevent="handleLogin"
        >
          <div>
            <label
              for="email"
              class="block text-sm/6 font-medium text-gray-900"
            >
              Email address
            </label>
            <div class="mt-2">
              <input
                id="email"
                v-model="email"
                name="email"
                type="email"
                autocomplete="email"
                required
                placeholder="Enter your SJTU email"
                class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
              />
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between">
              <label
                for="password"
                class="block text-sm/6 font-medium text-gray-900"
              >
                Password
              </label>
              <div class="text-sm">
                <router-link
                  to="/accounts/reset"
                  class="font-semibold text-indigo-600 hover:text-indigo-500"
                >
                  Forgot password?
                </router-link>
              </div>
            </div>
            <div class="mt-2">
              <input
                id="password"
                v-model="password"
                name="password"
                type="password"
                autocomplete="current-password"
                required
                placeholder="Enter your password"
                class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
              />
            </div>
          </div>

          <div>
            <Turnstile
              v-if="!showQuestionnaireLogin"
              key="login-password-turnstile"
              :show-title="false"
              theme="light"
              size="normal"
              @token="onTurnstileToken"
              @error="onTurnstileError"
              @expired="onTurnstileExpired"
            />
          </div>

          <div>
            <button
              type="submit"
              :disabled="loading || !turnstileToken"
              class="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm/6 font-semibold text-white shadow-sm hover:bg-indigo-500 focus:outline-2 focus:outline-offset-2 focus:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg
                v-if="loading"
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
              {{ loading ? "Signing in..." : "Sign in" }}
            </button>
          </div>
        </form>

        <!-- SJTU Authentication -->
        <div v-else>
          <AuthInitiate action="login" />
        </div>
      </div>

      <p class="mt-10 text-center text-sm/6 text-gray-500">
        Don't have an account?
        <router-link
          to="/accounts/signup"
          class="font-semibold leading-6 text-indigo-600 hover:text-indigo-500"
        >
          Sign up here
        </router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../composables/useAuth";
import { getCookie } from "../utils/cookies";
import { ExclamationTriangleIcon } from "@heroicons/vue/24/outline";
import AuthInitiate from "../components/AuthInitiate.vue";
import Turnstile from "../components/Turnstile.vue";

const router = useRouter();
const { isAuthenticated } = useAuth();
const email = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);
const showQuestionnaireLogin = ref(false);
const turnstileToken = ref(null);

// Turnstile event handlers
const onTurnstileToken = (token) => {
  turnstileToken.value = token;
};

const onTurnstileError = (errorMessage) => {
  error.value = errorMessage;
};

const onTurnstileExpired = (errorMessage) => {
  turnstileToken.value = null;
  error.value = errorMessage;
};

onMounted(async () => {
  // useAuth performs initial check; redirect if already authenticated
  if (isAuthenticated.value) {
    router.push("/courses");
  }
});

const handleLogin = async () => {
  error.value = "";

  // Check if turnstile token is available
  if (!turnstileToken.value) {
    error.value = "Please complete the security verification first.";
    return;
  }

  // Prevent sending development/mock tokens to backend which will fail verification.
  const mockPrefix = "dev-turnstile-token-";
  if (turnstileToken.value && turnstileToken.value.startsWith(mockPrefix)) {
    error.value =
      "Security verification is currently running in local mock mode. The server cannot verify mock tokens.\n" +
      "Disable mock mode (unset VITE_TURNSTILE_MOCK) or ensure Turnstile script can be loaded to proceed.";
    loading.value = false;
    return;
  }

  loading.value = true;

  try {
    const response = await fetch("/api/auth/login/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        email: email.value,
        password: password.value,
        turnstile_token: turnstileToken.value,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Login failed");
    }

    // Notify other parts of the app that authentication state changed
    try {
      window.dispatchEvent(new CustomEvent("auth-state-changed"));
    } catch (e) {
      console.warn("Could not dispatch auth-state-changed event:", e);
    }
    router.replace("/courses");
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
};

// getCookie imported from utils/cookies.js
</script>
