<template>
  <div
    class="flex min-h-full flex-1 flex-col justify-center px-6 py-12 lg:px-8"
  >
    <!-- Header Section -->
    <div class="sm:mx-auto sm:w-full sm:max-w-sm">
      <h2
        class="mt-10 text-center text-2xl/9 font-bold tracking-tight text-gray-900"
      >
        Sign in with SJTU Account
      </h2>
      <p class="mt-2 text-center text-sm/6 text-gray-500">
        Use your university credentials to authenticate
      </p>
    </div>

    <!-- Auth Card -->
    <div class="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
      <div
        class="overflow-hidden rounded-lg bg-white shadow-sm border border-gray-200"
      >
        <div class="px-4 py-5 sm:p-6">
          <!-- Loading State -->
          <div v-if="loading" class="text-center">
            <div
              class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"
            ></div>
            <p class="mt-2 text-sm text-gray-500">Loading authentication...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="rounded-md bg-red-50 p-4 mb-4">
            <div class="flex">
              <div class="ml-3">
                <h3 class="text-sm font-medium text-red-800">
                  Authentication Error
                </h3>
                <div class="mt-2 text-sm text-red-700">
                  <p>{{ error }}</p>
                </div>
                <div class="mt-4">
                  <div class="-mx-2 -my-1.5 flex">
                    <button
                      id="retry-auth-button"
                      name="retry-auth"
                      @click="resetAuth"
                      type="button"
                      class="rounded-md bg-red-50 px-2 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 1: Turnstile Widget -->
          <div v-else-if="!turnstileToken" class="space-y-4">
            <div class="text-center">
              <h3 class="text-lg font-medium text-gray-900 mb-2">
                Verify you're human
              </h3>
              <p class="text-sm text-gray-500 mb-4">
                Complete the security check below to continue
              </p>
            </div>

            <!-- Turnstile Widget Container -->
            <div class="flex justify-center">
              <div id="turnstile-widget" name="turnstile-widget"></div>
            </div>
          </div>

          <!-- Step 2: Ready to Sign In -->
          <div v-else class="space-y-4">
            <div class="rounded-md bg-green-50 p-4">
              <div class="flex">
                <div class="ml-3">
                  <h3 class="text-sm font-medium text-green-800">
                    Security Check Complete
                  </h3>
                  <div class="mt-2 text-sm text-green-700">
                    <p>
                      You can now proceed to authenticate with your SJTU
                      account.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <button
              id="continue-auth-button"
              name="continue-auth"
              @click="initiateLogin"
              :disabled="initiating"
              type="button"
              class="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="!initiating">Continue to SJTU Authentication</span>
              <span v-else class="flex items-center">
                <svg
                  class="animate-spin -ml-1 mr-3 h-4 w-4 text-white"
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
                Redirecting...
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from "vue";

// Reactive state
const turnstileToken = ref(null);
const loading = ref(true);
const error = ref(null);
const initiating = ref(false);

let turnstileWidget = null;

// Load Cloudflare Turnstile script
const loadTurnstile = () => {
  return new Promise((resolve, reject) => {
    // Check if Turnstile is already loaded
    if (window.turnstile) {
      resolve();
      return;
    }

    // Check if script is already being loaded
    const existingScript = document.querySelector('script[src*="turnstile"]');
    if (existingScript) {
      existingScript.onload = resolve;
      existingScript.onerror = reject;
      return;
    }

    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

// Initialize Turnstile widget
const initializeTurnstile = async () => {
  try {
    // Set loading to false so the Turnstile container is rendered in DOM
    loading.value = false;

    // Wait for Vue to update the DOM with the container
    await nextTick();

    // Double-check that the DOM element exists
    const widgetContainer = document.getElementById("turnstile-widget");
    if (!widgetContainer) {
      throw new Error("Turnstile widget container not found in DOM");
    }

    await loadTurnstile();

    // Clean up existing widget if present
    if (turnstileWidget) {
      try {
        window.turnstile.remove(turnstileWidget);
      } catch (e) {
        console.warn("Could not remove existing Turnstile widget:", e);
      }
    }

    turnstileWidget = window.turnstile.render("#turnstile-widget", {
      sitekey: import.meta.env.VITE_TURNSTILE_SITE_KEY,
      callback: (token) => {
        turnstileToken.value = token;
      },
      "error-callback": (errorCode) => {
        console.error("Turnstile error:", errorCode);
        error.value =
          "Security verification failed. Please refresh the page and try again.";
      },
      "expired-callback": () => {
        turnstileToken.value = null;
        error.value =
          "Security verification expired. Please complete the check again.";
      },
      theme: "light",
      size: "normal",
    });
  } catch (err) {
    console.error("Failed to load Turnstile:", err);
    error.value =
      "Failed to load security verification. Please check your internet connection and refresh the page.";
    loading.value = false;
  }
};

// Call the backend API to initiate login
const initiateLogin = async () => {
  if (!turnstileToken.value) {
    error.value = "Please complete the security verification first.";
    return;
  }

  initiating.value = true;
  error.value = null;

  try {
    const response = await fetch("/api/auth/initiate/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      credentials: "include",
      body: JSON.stringify({
        turnstile_token: turnstileToken.value,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      // Redirect to the questionnaire
      window.location.href = data.redirect_url;
    } else {
      error.value = data.error || "Authentication failed. Please try again.";
      initiating.value = false;
    }
  } catch (err) {
    console.error("API call failed:", err);
    error.value = "Network error. Please check your connection and try again.";
    initiating.value = false;
  }
};

// Get cookie value by name
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

// Reset authentication state
const resetAuth = () => {
  error.value = null;
  turnstileToken.value = null;
  loading.value = true;

  // Reset turnstile widget
  if (turnstileWidget && window.turnstile) {
    window.turnstile.reset(turnstileWidget);
  }

  // Reinitialize after DOM updates
  setTimeout(() => {
    initializeTurnstile();
  }, 100);
};

// Component lifecycle
onMounted(() => {
  initializeTurnstile();
});

onUnmounted(() => {
  // Clean up Turnstile widget if needed
  if (turnstileWidget && window.turnstile) {
    window.turnstile.remove(turnstileWidget);
  }
});
</script>

<style scoped>
/* Additional styles if needed */
</style>
