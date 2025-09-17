<template>
  <div
    class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8"
  >
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="text-center">
        <h2
          class="mt-6 text-center text-2xl/9 font-bold tracking-tight text-gray-900"
        >
          Reset your password
        </h2>
        <p class="mt-2 text-sm text-gray-600">
          Forgot your password? Verify your identity to reset it
        </p>
        <p class="mt-2 text-sm text-gray-600">
          Or
          <router-link
            to="/accounts/login"
            class="font-semibold text-indigo-600 hover:text-indigo-500"
          >
            back to sign in
          </router-link>
        </p>
      </div>
    </div>

    <div class="mt-10 sm:mx-auto sm:w-full sm:max-w-2xl">
      <!-- Enhanced Progress indicator -->
      <div class="bg-white py-8 px-6 shadow-sm sm:rounded-lg sm:px-8 mb-6">
        <div class="flex items-center justify-center">
          <div class="flex items-center space-x-8">
            <!-- Step 1 -->
            <div class="flex flex-col items-center">
              <div
                :class="[
                  'flex size-10 items-center justify-center rounded-full border-2 transition-colors duration-200',
                  currentStep >= 1
                    ? 'border-indigo-600 bg-indigo-600 text-white'
                    : 'border-gray-300 bg-white text-gray-500',
                ]"
              >
                <svg
                  v-if="currentStep > 1"
                  class="size-6 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clip-rule="evenodd"
                  ></path>
                </svg>
                <span v-else class="text-sm font-semibold">1</span>
              </div>
              <div class="mt-3 text-center">
                <div class="text-sm font-medium text-gray-900">Identity</div>
                <div class="text-xs text-gray-500">Verify your identity</div>
              </div>
            </div>

            <!-- Connecting line -->
            <div
              class="flex-1 h-px bg-gray-300 mx-4"
              :class="currentStep >= 2 ? 'bg-indigo-600' : 'bg-gray-300'"
            ></div>

            <!-- Step 2 -->
            <div class="flex flex-col items-center">
              <div
                :class="[
                  'flex size-10 items-center justify-center rounded-full border-2 transition-colors duration-200',
                  currentStep >= 2
                    ? 'border-indigo-600 bg-indigo-600 text-white'
                    : 'border-gray-300 bg-white text-gray-500',
                ]"
              >
                <svg
                  v-if="currentStep > 2"
                  class="size-6 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clip-rule="evenodd"
                  ></path>
                </svg>
                <span v-else class="text-sm font-semibold">2</span>
              </div>
              <div class="mt-3 text-center">
                <div class="text-sm font-medium text-gray-900">Password</div>
                <div class="text-xs text-gray-500">Set new password</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 1: Identity Verification -->
      <AuthInitiate
        v-if="currentStep === 1"
        action="reset_password"
        :key="authKey"
        @verified="handleVerified"
        @error="handleAuthError"
      />

      <!-- Step 2: Set New Password -->
      <SetPasswordForm
        v-else-if="currentStep === 2"
        mode="reset"
        :show-back-button="true"
        @success="handleResetSuccess"
        @error="handleResetError"
        @back="handleBack"
      />

      <!-- Step 3: Success Message -->
      <div
        v-else-if="currentStep === 3"
        class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10"
      >
        <div class="text-center">
          <div
            class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100"
          >
            <svg
              class="h-6 w-6 text-green-600"
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
          </div>
          <h3 class="mt-4 text-lg/7 font-medium text-gray-900">
            Password reset successful!
          </h3>
          <p class="mt-2 text-sm/6 text-gray-600">
            Your password has been reset successfully. You can now sign in with
            your new password.
          </p>
          <div class="mt-6 space-y-3">
            <button
              @click="goToLogin"
              class="w-full flex justify-center py-2 px-3 border border-transparent rounded-md shadow-sm text-sm/6 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
            >
              Sign in now
            </button>
            <router-link
              to="/"
              class="w-full flex justify-center py-2 px-3 border border-gray-300 rounded-md shadow-sm text-sm/6 font-semibold text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
            >
              Back to home
            </router-link>
          </div>
          <div class="mt-4 text-xs/5 text-gray-500">
            {{
              redirectCountdown > 0
                ? `Redirecting to sign in page in ${redirectCountdown} seconds`
                : ""
            }}
          </div>
        </div>
      </div>
    </div>

    <!-- Help Text -->
    <div
      v-if="currentStep === 1"
      class="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl"
    >
      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg
              class="size-5 text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              ></path>
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-indigo-800">
              Password Reset Instructions
            </h3>
            <div class="mt-2 text-sm/6 text-indigo-700">
              <ul class="list-disc list-inside space-y-1">
                <li>First, verify your identity through SJTU authentication</li>
                <li>
                  After successful verification, you can set a new password
                </li>
                <li>
                  Ensure your new password is secure (contains letters and
                  numbers, at least 12 characters)
                </li>
                <li>Keep your new password safe after resetting</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Security Notice -->
    <div
      v-if="currentStep === 2"
      class="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl"
    >
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg
              class="size-5 text-yellow-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z"
              ></path>
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-yellow-800">
              Security Reminder
            </h3>
            <div class="mt-2 text-sm/6 text-yellow-700">
              <p>
                For your account security, please set a strong password and
                change it regularly. Do not share your password with others.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Toast with enhanced design -->
    <div
      v-if="showErrorToast"
      class="fixed bottom-4 right-4 max-w-sm bg-red-50 border border-red-200 rounded-lg shadow-lg z-50 transform transition-all duration-300"
      :class="
        errorToastVisible
          ? 'translate-y-0 opacity-100'
          : 'translate-y-2 opacity-0'
      "
    >
      <div class="p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg
              class="size-5 text-red-400"
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
          <div class="ml-3">
            <p class="text-sm/6 font-medium text-red-800">
              {{ errorToastMessage }}
            </p>
          </div>
          <div class="ml-auto pl-3">
            <div class="-mx-1.5 -my-1.5">
              <button
                @click="hideErrorToast"
                class="inline-flex bg-red-50 rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
              >
                <svg
                  class="h-3 w-3"
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
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import AuthInitiate from "../components/AuthInitiate.vue";
import SetPasswordForm from "../components/SetPasswordForm.vue";

export default {
  name: "ResetPassword",
  components: {
    AuthInitiate,
    SetPasswordForm,
  },
  setup() {
    const router = useRouter();

    // Reactive state
    const currentStep = ref(1);
    const authKey = ref(0); // Used to force re-render AuthInitiate
    const showErrorToast = ref(false);
    const errorToastVisible = ref(false);
    const errorToastMessage = ref("");
    const redirectCountdown = ref(0);

    // Timer references
    let errorToastTimer = null;
    let redirectTimer = null;
    let countdownTimer = null;

    // Helper functions
    function getAuthState() {
      try {
        // Check URL parameters first (most reliable way)
        const urlParams = new URLSearchParams(window.location.search);
        if (
          urlParams.get("verified") === "true" &&
          urlParams.get("from_callback") === "true"
        ) {
          const urlAuthState = {
            status: "verified",
            action: urlParams.get("action"),
            account: urlParams.get("account"),
            expires_at: urlParams.get("expires_at"),
            verified_at: new Date().toISOString(),
            source: "url_params",
          };
          return urlAuthState;
        }

        // Then check localStorage
        const localStorageState = localStorage.getItem("auth_flow");
        if (localStorageState) {
          const parsed = JSON.parse(localStorageState);
          return { ...parsed, source: "localStorage" };
        }

        // Finally check sessionStorage
        const sessionStorageState = sessionStorage.getItem("auth_flow");
        if (sessionStorageState) {
          const parsed = JSON.parse(sessionStorageState);
          return { ...parsed, source: "sessionStorage" };
        }

        // Check backup sessionStorage key
        const backupSessionState = sessionStorage.getItem(
          "auth_verification_data",
        );
        if (backupSessionState) {
          const parsed = JSON.parse(backupSessionState);
          return { ...parsed, source: "sessionStorage_backup" };
        }

        return null;
      } catch (error) {
        console.error("Error reading auth state:", error);
        return null;
      }
    }

    function clearAuthState() {
      try {
        localStorage.removeItem("auth_flow");
        sessionStorage.removeItem("auth_flow");
        sessionStorage.removeItem("auth_verification_data");
        localStorage.removeItem("authState"); // Keep for backward compatibility
      } catch (error) {
        console.error("Failed to clear auth state:", error);
      }
    }

    function showErrorToastMessage(message) {
      errorToastMessage.value = message;
      showErrorToast.value = true;

      // Trigger animation
      setTimeout(() => {
        errorToastVisible.value = true;
      }, 10);

      // Auto hide after 5 seconds
      if (errorToastTimer) {
        clearTimeout(errorToastTimer);
      }
      errorToastTimer = setTimeout(hideErrorToast, 5000);
    }

    function hideErrorToast() {
      errorToastVisible.value = false;
      setTimeout(() => {
        showErrorToast.value = false;
      }, 300);

      if (errorToastTimer) {
        clearTimeout(errorToastTimer);
        errorToastTimer = null;
      }
    }

    function startRedirectCountdown() {
      redirectCountdown.value = 5;
      countdownTimer = setInterval(() => {
        redirectCountdown.value--;
        if (redirectCountdown.value <= 0) {
          clearInterval(countdownTimer);
          goToLogin();
        }
      }, 1000);
    }

    // Event handlers
    function handleVerified() {
      currentStep.value = 2;
    }

    function handleAuthError(error) {
      console.error("Auth error:", error);
      showErrorToastMessage(error.message || "Identity verification failed");
    }

    function handleResetSuccess(event) {
      currentStep.value = 3;

      // Start redirect countdown
      redirectTimer = setTimeout(() => {
        startRedirectCountdown();
      }, 1000);
    }

    function handleResetError(error) {
      console.error("Password reset error:", error);
      showErrorToastMessage(error.message || "Password reset failed");
    }

    function handleBack() {
      // Clear auth state and go back to step 1
      clearAuthState();
      currentStep.value = 1;
      authKey.value++; // Force re-render
    }

    function goToLogin() {
      // Clear any timers
      if (redirectTimer) clearTimeout(redirectTimer);
      if (countdownTimer) clearInterval(countdownTimer);

      router.push("/accounts/login");
    }

    // Lifecycle hooks
    onMounted(() => {
      // Check if there's an existing auth state
      const authState = getAuthState();

      if (authState) {
        // If the user is verified but came back to reset page
        if (
          authState.action === "reset_password" &&
          authState.status === "verified"
        ) {
          // If state comes from URL parameters, save it to localStorage
          if (authState.source === "url_params") {
            const stateToSave = { ...authState };
            delete stateToSave.source; // Remove source field
            localStorage.setItem("auth_flow", JSON.stringify(stateToSave));
            sessionStorage.setItem("auth_flow", JSON.stringify(stateToSave));
          }

          currentStep.value = 2;
        } else if (authState.action !== "reset_password") {
          // Wrong action, clear state and start over
          clearAuthState();
          currentStep.value = 1;
        }
      }

      // Clear any existing auth state for fresh start
      // This ensures we don't have stale state from other auth flows
      const freshState = getAuthState();
      if (freshState && freshState.action !== "reset_password") {
        clearAuthState();
      }
    });

    onUnmounted(() => {
      // Clean up timers
      if (errorToastTimer) clearTimeout(errorToastTimer);
      if (redirectTimer) clearTimeout(redirectTimer);
      if (countdownTimer) clearInterval(countdownTimer);
    });

    return {
      currentStep,
      authKey,
      showErrorToast,
      errorToastVisible,
      errorToastMessage,
      redirectCountdown,
      handleVerified,
      handleAuthError,
      handleResetSuccess,
      handleResetError,
      handleBack,
      goToLogin,
      hideErrorToast,
    };
  },
};
</script>

<style scoped>
/* Custom animations for smooth transitions */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}

/* Progress bar animation */
.progress-bar {
  transition: width 0.3s ease-in-out;
}

/* Toast animation */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from,
.toast-leave-to {
  transform: translateY(0.5rem);
  opacity: 0;
}

/* Step indicator animations */
.step-indicator {
  transition: all 0.15s ease-in-out;
}

/* Focus styles for accessibility */
button:focus,
a:focus {
  outline: none;
}

/* Custom hover effects */
.hover-lift:hover {
  transform: translateY(-1px);
}

/* Info and warning box styling */
.info-box {
  background: linear-gradient(135deg, #ebf8ff 0%, #f0f9ff 100%);
}

.warning-box {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
}
</style>
