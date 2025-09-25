<template>
  <div class="auth-initiate">
    <div v-if="loading" class="text-center">
      <Icon name="loading" class="h-8 w-8 text-indigo-600 mx-auto" />
      <p class="mt-2 text-sm/6 text-gray-500">Loading authentication...</p>
    </div>

    <div v-else-if="error" class="rounded-lg bg-red-50 p-4 mb-4">
      <div class="flex">
        <div class="ml-3">
          <h3 class="text-sm/6 font-medium text-red-800">
            Authentication Error
          </h3>
          <div class="mt-2 text-sm/6 text-red-700">
            <p>{{ error }}</p>
          </div>
          <div class="mt-4">
            <button
              type="button"
              class="rounded-md bg-red-50 px-2 py-1.5 text-sm/6 font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
              @click="resetAuth"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="otpData" class="space-y-4">
      <div class="rounded-lg bg-indigo-50 p-4">
        <div class="text-center">
          <h3 class="text-lg/7 font-medium text-indigo-800 mb-2">
            Your Verification Code
          </h3>
          <div class="text-3xl font-mono font-bold text-indigo-900 mb-4">
            {{ otpData.otp }}
          </div>
          <p class="text-sm/6 text-indigo-700 mb-4">
            Copy this code and click continue to proceed to SJTU authentication
          </p>
          <div class="space-y-2">
            <button
              :disabled="redirecting"
              type="button"
              class="w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm/6 font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="copyOTPAndRedirect"
            >
              <span v-if="!redirecting">{{ copyButtonText }}</span>
              <span v-else class="flex items-center justify-center">
                <Icon
                  name="loading"
                  class="animate-spin -ml-1 mr-3 text-white"
                />
                Redirecting in {{ countdown }}s...
              </span>
            </button>

            <p class="text-xs/5 text-indigo-600">
              Expires in {{ formatTime(otpData.expires_at) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      v-else-if="!turnstileToken"
      class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10"
    >
      <Turnstile
        ref="turnstileRef"
        key="auth-initiate-turnstile"
        :show-title="true"
        theme="light"
        size="normal"
        @token="onTurnstileToken"
        @error="onTurnstileError"
        @expired="onTurnstileExpired"
      />
    </div>

    <div v-else class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10">
      <div class="space-y-4">
        <div class="rounded-lg bg-green-50 p-4">
          <div class="flex">
            <div class="ml-3">
              <h3 class="text-sm/6 font-medium text-green-800">
                Security Check Complete
              </h3>
              <div class="mt-2 text-sm/6 text-green-700">
                <p>
                  Ready to initiate {{ action }} process with SJTU
                  authentication.
                </p>
              </div>
            </div>
          </div>
        </div>
        <button
          :disabled="initiating"
          type="button"
          class="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm/6 font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
          @click="initiateAuth"
        >
          <span v-if="!initiating">Continue with SJTU Authentication</span>
          <span v-else class="flex items-center">
            <Icon name="loading" class="animate-spin -ml-1 mr-3 text-white" />
            Initializing...
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { getCookie } from "../utils/cookies";
import { clearAuthState } from "../utils/auth";
import Turnstile from "./Turnstile.vue";
import Icon from "./Icon.vue";

const props = defineProps({
  action: {
    type: String,
    required: true,
    validator: (value) => ["signup", "login", "reset_password"].includes(value),
  },
});

const loading = ref(true);
const error = ref(null);
const turnstileToken = ref(null);
const otpData = ref(null);
const initiating = ref(false);
const redirecting = ref(false);
const copyButtonText = ref("Copy Code & Continue");
const countdown = ref(0);
const redirectUrl = ref(null);
const currentTime = ref(Date.now());
const turnstileRef = ref(null);

let countdownInterval = null;
let timeUpdateInterval = null;

const onTurnstileToken = (token) => {
  turnstileToken.value = token;
  loading.value = false;
};

const onTurnstileError = (errorMessage) => {
  console.error("Turnstile error:", errorMessage);
  error.value = errorMessage;
  loading.value = false;
};

const onTurnstileExpired = (errorMessage) => {
  turnstileToken.value = null;
  error.value = errorMessage;
};
const checkExistingOTP = () => {
  const storedOTP = localStorage.getItem("auth_otp");
  const storedFlow = localStorage.getItem("auth_flow");

  if (storedOTP) {
    try {
      const otpInfo = JSON.parse(storedOTP);
      const flowInfo = storedFlow ? JSON.parse(storedFlow) : null;

      // Check if OTP is not expired and flow state matches
      if (
        otpInfo.expires_at > Date.now() &&
        flowInfo &&
        flowInfo.action === props.action &&
        flowInfo.status === "pending"
      ) {
        otpData.value = otpInfo;
        return true;
      } else {
        // Clear expired OTP and auth flow state records
        clearAuthData();
      }
    } catch (e) {
      console.error("Error parsing stored OTP data:", e);
      clearAuthData();
    }
  }
  return false;
};

const clearAuthData = () => {
  clearAuthState();
};

const initiateAuth = async () => {
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
        action: props.action,
        turnstile_token: turnstileToken.value,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      const expiresAt = Date.now() + 2 * 60 * 1000;
      const otpInfo = {
        otp: data.otp,
        expires_at: expiresAt,
      };
      const flowInfo = {
        status: "pending",
        action: props.action,
        expires_at: Date.now() + 10 * 60 * 1000,
        redirect_url: data.redirect_url, // Store redirect URL
      };

      localStorage.setItem("auth_otp", JSON.stringify(otpInfo));
      localStorage.setItem("auth_flow", JSON.stringify(flowInfo));

      otpData.value = otpInfo;
      redirectUrl.value = data.redirect_url;
    } else {
      error.value =
        data.error || "Authentication initialization failed. Please try again.";
    }
  } catch (err) {
    console.error("API call failed:", err);
    error.value = "Network error. Please check your connection and try again.";
  } finally {
    initiating.value = false;
  }
};

const copyOTPAndRedirect = async () => {
  if (!otpData.value) {
    console.error("No OTP data available");
    return;
  }

  if (!redirectUrl.value) {
    console.error("No redirect URL available, trying to get from localStorage");
    // Try to get redirect URL from localStorage
    const storedFlow = localStorage.getItem("auth_flow");
    if (storedFlow) {
      try {
        const flowInfo = JSON.parse(storedFlow);
        redirectUrl.value = flowInfo.redirect_url;
      } catch (e) {
        console.error("Error parsing stored flow:", e);
        return;
      }
    }

    if (!redirectUrl.value) {
      console.error("Still no redirect URL available");
      return;
    }
  }

  try {
    localStorage.setItem("auth_redirect_time", Date.now().toString());

    await navigator.clipboard.writeText(otpData.value.otp);
    copyButtonText.value = "Copied!";

    redirecting.value = true;
    countdown.value = 1;

    countdownInterval = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(countdownInterval);
        const url = new URL(redirectUrl.value);
        url.searchParams.set("otp_hint", otpData.value.otp);
        window.location.href = url.toString();
      }
    }, 1000);
  } catch (err) {
    console.error("Failed to copy to clipboard:", err);
    setTimeout(() => {
      const url = new URL(redirectUrl.value);
      url.searchParams.set("otp_hint", otpData.value.otp);
      window.location.href = url.toString();
    }, 1000);
  }
};

const formatTime = (expiresAt) => {
  const remaining = Math.max(
    0,
    Math.floor((expiresAt - currentTime.value) / 1000),
  );
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

const resetAuth = () => {
  // Clear all state
  error.value = null;
  turnstileToken.value = null;
  otpData.value = null;
  redirecting.value = false;
  copyButtonText.value = "Copy Code & Continue";
  countdown.value = 0;
  redirectUrl.value = null;

  // Clear intervals
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }

  // Clear auth data
  clearAuthData();

  // Reset Turnstile widget if available
  if (turnstileRef.value && turnstileRef.value.resetTurnstile) {
    turnstileRef.value.resetTurnstile();
  }

  // Set loading state briefly to show reset
  loading.value = true;

  setTimeout(() => {
    loading.value = false;
  }, 300);
};

onMounted(async () => {
  // Clear any existing intervals
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }

  timeUpdateInterval = setInterval(() => {
    currentTime.value = Date.now();
  }, 1000);

  // Check for existing OTP first
  const hasExistingOTP = checkExistingOTP();

  if (hasExistingOTP) {
    // If we have existing OTP data, restore redirect URL
    const storedFlow = localStorage.getItem("auth_flow");
    if (storedFlow) {
      try {
        const flowInfo = JSON.parse(storedFlow);
        redirectUrl.value = flowInfo.redirect_url;

        // Reset button states for returning users
        redirecting.value = false;
        copyButtonText.value = "Copy Code & Continue";
        countdown.value = 0;

        // Clear any existing countdown interval
        if (countdownInterval) {
          clearInterval(countdownInterval);
          countdownInterval = null;
        }

        loading.value = false;
      } catch (e) {
        console.error("Error parsing flow data:", e);
        loading.value = false;
      }
    } else {
      loading.value = false;
      redirecting.value = false;
      copyButtonText.value = "Copy Code & Continue";
      countdown.value = 0;
    }
  } else {
    // Reset all state when starting fresh
    loading.value = false;
    error.value = null;
    turnstileToken.value = null;
    otpData.value = null;
    redirecting.value = false;
    copyButtonText.value = "Copy Code & Continue";
    countdown.value = 0;
    redirectUrl.value = null;

    // Reset Turnstile when starting fresh
    setTimeout(() => {
      if (turnstileRef.value && turnstileRef.value.resetTurnstile) {
        turnstileRef.value.resetTurnstile();
      }
    }, 100);
  }
});

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
  }
});
</script>

<style scoped>
.auth-initiate {
  max-width: 100%;
}
</style>
