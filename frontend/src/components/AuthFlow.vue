<template>
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
              <div class="text-xs text-gray-500">{{ passwordLabel }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 1: Identity Verification -->
    <AuthInitiate
      v-if="currentStep === 1"
      :key="authKey"
      :action="action"
      @verified="handleVerified"
      @error="handleAuthError"
    />

    <!-- Step 2: Set Password -->
    <SetPasswordForm
      v-else-if="currentStep === 2"
      :mode="setPasswordMode"
      :show-back-button="true"
      @success="handleSuccess"
      @error="handleError"
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
          {{ successTitle }}
        </h3>
        <p class="mt-2 text-sm/6 text-gray-600">{{ successMessage }}</p>
        <div class="mt-6 space-y-3">
          <button
            class="w-full flex justify-center py-2 px-3 border border-transparent rounded-md shadow-sm text-sm/6 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
            @click="goToLogin"
          >
            {{ successButtonText }}
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

    <!-- Help Text -->
    <div
      v-if="helpTitle && currentStep === 1"
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
              />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-indigo-800">
              {{ helpTitle }}
            </h3>
            <div class="mt-2 text-sm/6 text-indigo-700">
              <ul class="list-disc list-inside space-y-1">
                <li v-for="(item, idx) in helpItems" :key="idx">{{ item }}</li>
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
              />
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
              />
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
                class="inline-flex bg-red-50 rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
                @click="hideErrorToast"
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
                  />
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
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import AuthInitiate from "../components/AuthInitiate.vue";
import SetPasswordForm from "../components/SetPasswordForm.vue";

export default {
  name: "AuthFlow",
  components: {
    AuthInitiate,
    SetPasswordForm,
  },
  props: {
    action: {
      type: String,
      required: true,
    },
    passwordLabel: {
      type: String,
      default: "Set new password",
    },
    setPasswordMode: {
      type: String,
      default: "reset",
    },
    successTitle: {
      type: String,
      default: "Success!",
    },
    successMessage: {
      type: String,
      default: "Operation completed successfully.",
    },
    successButtonText: {
      type: String,
      default: "Sign in now",
    },
    helpTitle: {
      type: String,
      default: "",
    },
    helpItems: {
      type: Array,
      default: () => [],
    },
  },
  setup(props) {
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

    // Helper functions (same as original)
    function getAuthState() {
      try {
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

        const localStorageState = localStorage.getItem("auth_flow");
        if (localStorageState) {
          const parsed = JSON.parse(localStorageState);
          return { ...parsed, source: "localStorage" };
        }

        const sessionStorageState = sessionStorage.getItem("auth_flow");
        if (sessionStorageState) {
          const parsed = JSON.parse(sessionStorageState);
          return { ...parsed, source: "sessionStorage" };
        }

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
        localStorage.removeItem("authState");
      } catch (error) {
        console.error("Failed to clear auth state:", error);
      }
    }

    function showErrorToastMessage(message) {
      errorToastMessage.value = message;
      showErrorToast.value = true;

      setTimeout(() => {
        errorToastVisible.value = true;
      }, 10);

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

    function handleSuccess() {
      currentStep.value = 3;
      redirectTimer = setTimeout(() => {
        startRedirectCountdown();
      }, 1000);
    }

    function handleError(error) {
      console.error("Operation error:", error);
      showErrorToastMessage(error.message || "Operation failed");
    }

    function handleBack() {
      clearAuthState();
      currentStep.value = 1;
      authKey.value++;
    }

    function goToLogin() {
      if (redirectTimer) clearTimeout(redirectTimer);
      if (countdownTimer) clearInterval(countdownTimer);

      router.push("/accounts/login");
    }

    onMounted(() => {
      const authState = getAuthState();

      if (authState) {
        if (
          authState.action === props.action &&
          authState.status === "verified"
        ) {
          if (authState.source === "url_params") {
            const stateToSave = { ...authState };
            delete stateToSave.source;
            localStorage.setItem("auth_flow", JSON.stringify(stateToSave));
            sessionStorage.setItem("auth_flow", JSON.stringify(stateToSave));
          }

          currentStep.value = 2;
        } else if (authState.action !== props.action) {
          clearAuthState();
          currentStep.value = 1;
        }
      }

      const freshState = getAuthState();
      if (freshState && freshState.action !== props.action) {
        clearAuthState();
      }
    });

    onUnmounted(() => {
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
      handleSuccess,
      handleError,
      handleBack,
      goToLogin,
    };
  },
};
</script>

<style scoped>
/* Keep styles small - component uses existing global utility classes */
</style>
