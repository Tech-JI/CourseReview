<template>
  <div class="mt-10 sm:mx-auto sm:w-full sm:max-w-2xl">
    <div class="bg-white py-8 px-6 shadow-sm sm:rounded-lg sm:px-8 mb-6">
      <div class="flex items-center justify-center">
        <div class="flex items-center space-x-8">
          <div class="flex flex-col items-center">
            <div
              :class="[
                'flex size-10 items-center justify-center rounded-full border-2 transition-colors duration-200',
                currentStep >= 1
                  ? 'border-indigo-600 bg-indigo-600 text-white'
                  : 'border-gray-300 bg-white text-gray-500',
              ]"
            >
              <Icon v-if="currentStep > 1" name="check" class="text-white" />
              <span v-else class="text-sm font-semibold">1</span>
            </div>
            <div class="mt-3 text-center">
              <div class="text-sm font-medium text-gray-900">Identity</div>
              <div class="text-xs text-gray-500">Verify your identity</div>
            </div>
          </div>

          <div
            class="flex-1 h-px bg-gray-300 mx-4"
            :class="currentStep >= 2 ? 'bg-indigo-600' : 'bg-gray-300'"
          ></div>

          <div class="flex flex-col items-center">
            <div
              :class="[
                'flex size-10 items-center justify-center rounded-full border-2 transition-colors duration-200',
                currentStep >= 2
                  ? 'border-indigo-600 bg-indigo-600 text-white'
                  : 'border-gray-300 bg-white text-gray-500',
              ]"
            >
              <Icon v-if="currentStep > 2" name="check" class="text-white" />
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

    <AuthInitiate
      v-if="currentStep === 1"
      :key="authKey"
      :action="action"
      @verified="handleVerified"
      @error="handleAuthError"
    />

    <SetPasswordForm
      v-else-if="currentStep === 2"
      :mode="setPasswordMode"
      :show-back-button="true"
      @success="handleSuccess"
      @error="handleError"
      @back="handleBack"
    />

    <div
      v-else-if="currentStep === 3"
      class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10"
    >
      <div class="text-center">
        <div
          class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100"
        >
          <Icon name="check-circle" class="text-green-600" />
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

    <div
      v-if="helpTitle && currentStep === 1"
      class="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl"
    >
      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <Icon name="info" class="text-indigo-400" />
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

    <div
      v-if="currentStep === 2"
      class="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl"
    >
      <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <Icon name="warning" class="text-yellow-400" />
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
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { clearAuthState, getAuthState, saveAuthState } from "../utils/auth";
import { useNotifications } from "../composables/useNotifications";
import AuthInitiate from "../components/AuthInitiate.vue";
import SetPasswordForm from "../components/SetPasswordForm.vue";
import Icon from "../components/Icon.vue";

export default {
  name: "AuthFlow",
  components: {
    AuthInitiate,
    SetPasswordForm,
    Icon,
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
    const { showError } = useNotifications();

    const currentStep = ref(1);
    const authKey = ref(0);
    const redirectCountdown = ref(0);

    let redirectTimer = null;
    let countdownTimer = null;

    function getAuthStateLocal() {
      return getAuthState();
    }

    function handleAuthError(error) {
      console.error("Auth error:", error);
      showError(error.message || "Identity verification failed");
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

    function handleVerified() {
      currentStep.value = 2;
    }

    function handleAuthError(error) {
      console.error("Auth error:", error);
      showError(error.message || "Identity verification failed");
    }

    function handleSuccess() {
      currentStep.value = 3;
      redirectTimer = setTimeout(() => {
        startRedirectCountdown();
      }, 1000);
    }

    function handleError(error) {
      console.error("Operation error:", error);
      showError(error.message || "Operation failed");
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
      const authState = getAuthStateLocal();

      if (authState) {
        if (
          authState.action === props.action &&
          authState.status === "verified"
        ) {
          if (authState.source === "url_params") {
            saveAuthState(authState, true);
          }

          currentStep.value = 2;
        } else if (authState.action !== props.action) {
          clearAuthState();
          currentStep.value = 1;
        }
      }
    });

    onUnmounted(() => {
      if (redirectTimer) clearTimeout(redirectTimer);
      if (countdownTimer) clearInterval(countdownTimer);
    });

    return {
      currentStep,
      authKey,
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
