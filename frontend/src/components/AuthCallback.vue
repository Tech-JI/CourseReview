<template>
  <div
    class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8"
  >
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="text-center">
        <div class="mx-auto h-12 w-12 text-blue-600">
          <svg
            v-if="isLoading"
            class="animate-spin h-12 w-12 text-blue-600"
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
          <svg
            v-else-if="isSuccess"
            class="h-12 w-12 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M5 13l4 4L19 7"
            ></path>
          </svg>
          <svg
            v-else
            class="h-12 w-12 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          {{ pageTitle }}
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ pageDescription }}
        </p>
      </div>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
        <!-- Loading State -->
        <div v-if="isLoading" class="text-center">
          <div class="text-base text-gray-600 mb-4">
            Verifying your identity...
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
              :style="{ width: progressPercentage + '%' }"
            ></div>
          </div>
          <div class="text-xs text-gray-500 mt-2">
            Please wait, this usually takes a few seconds
          </div>
        </div>

        <!-- Success State -->
        <div v-else-if="isSuccess" class="text-center">
          <div class="text-base text-green-600 mb-4">
            {{ successMessage }}
          </div>
          <div class="space-y-3">
            <button
              @click="handleRedirect"
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-150 ease-in-out"
            >
              {{ redirectButtonText }}
            </button>
            <div class="text-xs text-gray-500">
              {{
                redirectCountdown > 0
                  ? `Auto-redirecting in ${redirectCountdown} seconds`
                  : ""
              }}
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-else class="text-center">
          <div class="text-base text-red-600 mb-4">
            {{ errorMessage }}
          </div>
          <div class="space-y-3">
            <button
              @click="retryVerification"
              v-if="canRetry"
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition duration-150 ease-in-out"
            >
              Retry Verification
            </button>
            <button
              @click="goBack"
              class="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-150 ease-in-out"
            >
              Go Back
            </button>
          </div>
        </div>

        <!-- Debug Info (development only) -->
        <div
          v-if="isDevelopment && debugInfo"
          class="mt-6 p-4 bg-gray-100 rounded-md"
        >
          <div class="text-xs text-gray-600 font-mono">
            <div><strong>Status ID:</strong> {{ debugInfo.statusId }}</div>
            <div><strong>Action:</strong> {{ debugInfo.action }}</div>
            <div>
              <strong>URL Parameters:</strong>
              {{ JSON.stringify(debugInfo.urlParams) }}
            </div>
            <div v-if="debugInfo.error">
              <strong>Error:</strong> {{ debugInfo.error }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";

export default {
  name: "AuthCallback",
  setup() {
    const route = useRoute();
    const router = useRouter();

    // Reactive state
    const isLoading = ref(true);
    const isSuccess = ref(false);
    const errorMessage = ref("");
    const successMessage = ref("");
    const canRetry = ref(false);
    const redirectCountdown = ref(0);
    const progressPercentage = ref(0);
    const debugInfo = ref(null);

    // Constants
    const isDevelopment = process.env.NODE_ENV === "development";
    const REDIRECT_DELAY = 1000; // 1 second
    const PROGRESS_STEPS = [20, 50, 80, 100];

    // Computed properties
    const pageTitle = computed(() => {
      if (isLoading.value) return "Authenticating";
      if (isSuccess.value) return "Verification Successful";
      return "Verification Failed";
    });

    const pageDescription = computed(() => {
      if (isLoading.value) return "Processing your login request";
      if (isSuccess.value) return "You have successfully authenticated";
      return "An issue occurred during verification";
    });

    const redirectButtonText = computed(() => {
      const action = route.query.action || "login";
      switch (action) {
        case "signup":
          return "Continue Registration";
        case "reset_password":
          return "Continue Password Reset";
        case "login":
        default:
          return "Go to Homepage";
      }
    });

    // Timer references
    let progressTimer = null;
    let redirectTimer = null;
    let countdownTimer = null;

    // Helper functions
    function getActionFromStorage() {
      try {
        const authState = localStorage.getItem("auth_flow");
        return authState ? JSON.parse(authState).action : "login";
      } catch {
        return "login";
      }
    }

    function updateAuthState(updates) {
      try {
        const currentState = localStorage.getItem("auth_flow");
        const state = currentState ? JSON.parse(currentState) : {};
        const newState = { ...state, ...updates };
        localStorage.setItem("auth_flow", JSON.stringify(newState));
      } catch (error) {
        console.error("Failed to update auth state:", error);
      }
    }

    function clearAuthState() {
      try {
        localStorage.removeItem("auth_flow");
      } catch (error) {
        console.error("Failed to clear auth state:", error);
      }
    }

    function startProgressAnimation() {
      let stepIndex = 0;
      progressTimer = setInterval(() => {
        if (stepIndex < PROGRESS_STEPS.length) {
          progressPercentage.value = PROGRESS_STEPS[stepIndex];
          stepIndex++;
        }
      }, 800);
    }

    function stopProgressAnimation() {
      if (progressTimer) {
        clearInterval(progressTimer);
        progressTimer = null;
      }
    }

    function startRedirectCountdown() {
      redirectCountdown.value = Math.ceil(REDIRECT_DELAY / 1000);
      countdownTimer = setInterval(() => {
        redirectCountdown.value--;
        if (redirectCountdown.value <= 0) {
          clearInterval(countdownTimer);
          handleRedirect();
        }
      }, 0);
    }

    async function verifyCallback() {
      try {
        // Get URL parameters
        const statusId = route.query.id;
        const account = route.query.account;
        const action = route.query.action;
        const urlParams = { ...route.query };

        // Set debug info for development
        if (isDevelopment) {
          debugInfo.value = {
            statusId,
            action: action,
            urlParams,
          };
        }

        // Validate required parameters
        if (!statusId) {
          throw new Error("Missing required verification parameters");
        }

        if (!account) {
          throw new Error("Missing account information");
        }

        if (!action) {
          throw new Error("Missing action type");
        }

        // Start progress animation
        startProgressAnimation();

        // Call verify API
        const response = await fetch("/api/auth/verify-callback/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          credentials: "include",
          body: JSON.stringify({
            status_id: statusId,
            ...urlParams,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || `Server error (${response.status})`);
        }

        // Handle successful verification
        stopProgressAnimation();
        progressPercentage.value = 100;

        isLoading.value = false;
        isSuccess.value = true;

        // Update auth state with verification result
        const updateData = {
          action: action,
          status: "verified",
          account: account,
          verificationData: data,
          completedAt: new Date().toISOString(),
          expires_at: Date.now() + 10 * 60 * 1000, // 10 minutes validity
        };

        // Set complete state directly instead of merging
        try {
          localStorage.setItem("auth_flow", JSON.stringify(updateData));
        } catch (localStorageError) {
          console.error("Failed to update localStorage:", localStorageError);
          throw localStorageError;
        }

        // Verify what was actually stored
        const updatedState = localStorage.getItem("auth_flow");
        try {
          const parsedState = JSON.parse(updatedState);
        } catch (e) {
          console.error("Failed to parse updated state:", e);
        }

        // Set success message based on action
        switch (action) {
          case "signup":
            successMessage.value =
              "Authentication successful! You can now set your account password";
            break;
          case "reset_password":
            successMessage.value =
              "Authentication successful! You can now reset your password";
            break;
          case "login":
          default:
            successMessage.value = "Login successful! Welcome back";
            // Trigger authentication state change event
            window.dispatchEvent(new CustomEvent("auth-state-changed"));
            break;
        }

        // Start redirect countdown
        redirectTimer = setTimeout(handleRedirect, REDIRECT_DELAY);
        startRedirectCountdown();
      } catch (error) {
        console.error("Verification failed:", error);

        stopProgressAnimation();
        isLoading.value = false;
        isSuccess.value = false;
        errorMessage.value =
          error.message || "An unknown error occurred during verification";
        canRetry.value = true;

        // Add error to debug info
        if (isDevelopment && debugInfo.value) {
          debugInfo.value.error = error.message;
        }
      }
    }

    function getCsrfToken() {
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        const [name, value] = cookie.trim().split("=");
        if (name === "csrftoken") {
          return value;
        }
      }
      return "";
    }

    function handleRedirect() {
      // Get action from URL parameters instead of localStorage
      const action = route.query.action || "login";

      const currentState = localStorage.getItem("auth_flow");

      switch (action) {
        case "signup":
          // Don't clear state for signup - Signup.vue needs it to show password form
          router.push("/accounts/signup");
          break;
        case "reset_password":
          // Don't clear state for reset - Reset.vue needs it to show password form
          router.push("/accounts/reset");
          break;
        case "login":
        default:
          // For login, check if we have a redirect URL and clean up
          try {
            const authState = localStorage.getItem("auth_flow");
            const state = authState ? JSON.parse(authState) : {};
            const redirectUrl = state.redirectUrl || "/";
            clearAuthState();
            router.push(redirectUrl);
          } catch {
            clearAuthState();
            router.push("/");
          }
          break;
      }
    }

    function retryVerification() {
      isLoading.value = true;
      isSuccess.value = false;
      errorMessage.value = "";
      canRetry.value = false;
      progressPercentage.value = 0;

      // Clear any existing timers
      if (redirectTimer) {
        clearTimeout(redirectTimer);
        redirectTimer = null;
      }
      if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }

      // Retry verification
      verifyCallback();
    }

    function goBack() {
      const action = route.query.action || "login";
      clearAuthState();

      switch (action) {
        case "signup":
          router.push("/accounts/signup");
          break;
        case "reset_password":
          router.push("/accounts/reset");
          break;
        case "login":
        default:
          router.push("/accounts/login");
          break;
      }
    }

    // Lifecycle hooks
    onMounted(() => {
      verifyCallback();
    });

    onUnmounted(() => {
      // Clean up timers
      if (progressTimer) clearInterval(progressTimer);
      if (redirectTimer) clearTimeout(redirectTimer);
      if (countdownTimer) clearInterval(countdownTimer);
    });

    return {
      isLoading,
      isSuccess,
      errorMessage,
      successMessage,
      canRetry,
      redirectCountdown,
      progressPercentage,
      debugInfo,
      isDevelopment,
      pageTitle,
      pageDescription,
      redirectButtonText,
      handleRedirect,
      retryVerification,
      goBack,
    };
  },
};
</script>

<style scoped>
/* Custom loading animation for better UX */
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Smooth transitions for state changes */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}
</style>
