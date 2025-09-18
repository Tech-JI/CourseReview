<template>
  <div class="auth-initiate">
    <!-- Loading State -->
    <div v-if="loading" class="text-center">
      <div
        class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"
      ></div>
      <p class="mt-2 text-sm/6 text-gray-500">Loading authentication...</p>
    </div>

    <!-- Error State -->
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
              @click="resetAuth"
              type="button"
              class="rounded-md bg-red-50 px-2 py-1.5 text-sm/6 font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- OTP Display and Copy -->
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
              @click="copyOTPAndRedirect"
              :disabled="redirecting"
              type="button"
              class="w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm/6 font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="!redirecting">{{ copyButtonText }}</span>
              <span v-else class="flex items-center justify-center">
                <svg
                  class="animate-spin -ml-1 mr-3 size-4 text-white"
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

    <!-- Turnstile Widget -->
    <div
      v-else-if="!turnstileToken"
      class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10"
    >
      <div class="space-y-4">
        <div class="text-center">
          <h3 class="text-lg/7 font-medium text-gray-900 mb-2">
            Verify you're human
          </h3>
          <p class="text-sm/6 text-gray-500 mb-4">
            Complete the security check below to continue
          </p>
        </div>
        <div class="flex justify-center">
          <div id="turnstile-widget"></div>
        </div>
      </div>
    </div>

    <!-- Ready to Initiate -->
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
          @click="initiateAuth"
          :disabled="initiating"
          type="button"
          class="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm/6 font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="!initiating">Continue with SJTU Authentication</span>
          <span v-else class="flex items-center">
            <svg
              class="animate-spin -ml-1 mr-3 size-4 text-white"
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
            Initializing...
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from "vue";

// Props
const props = defineProps({
  action: {
    type: String,
    required: true,
    validator: (value) => ["signup", "login", "reset_password"].includes(value),
  },
});

// Reactive state
const loading = ref(true);
const error = ref(null);
const turnstileToken = ref(null);
const otpData = ref(null);
const initiating = ref(false);
const redirecting = ref(false);
const copyButtonText = ref("Copy Code & Continue");
const countdown = ref(0);
const redirectUrl = ref(null);
const currentTime = ref(Date.now()); // For reactive countdown updates

// Turnstile management
let turnstileWidget = null;
let isInitializingTurnstile = false; // Prevent concurrent initialization

// Safe cleanup of existing turnstile widget
const cleanupTurnstile = () => {
  if (turnstileWidget && window.turnstile) {
    try {
      console.log("🔧 Debug: Removing existing turnstile widget");
      window.turnstile.remove(turnstileWidget);
    } catch (e) {
      console.warn("Error removing turnstile widget:", e);
    }
  }
  turnstileWidget = null;

  // Also clear the DOM container to ensure clean state
  const widgetContainer = document.getElementById("turnstile-widget");
  if (widgetContainer) {
    widgetContainer.innerHTML = "";
    console.log("🔧 Debug: Cleared turnstile widget container");
  }
};
let countdownInterval = null;
let timeUpdateInterval = null; // For updating currentTime

// Check for existing OTP data in localStorage
const checkExistingOTP = () => {
  const storedOTP = localStorage.getItem("auth_otp");
  const storedFlow = localStorage.getItem("auth_flow");

  if (storedOTP) {
    try {
      const otpInfo = JSON.parse(storedOTP);
      const flowInfo = storedFlow ? JSON.parse(storedFlow) : null;

      // Check if OTP is still valid and matches current action
      if (
        otpInfo.expires_at > Date.now() &&
        flowInfo &&
        flowInfo.action === props.action &&
        flowInfo.status === "pending"
      ) {
        // Check if too much time has passed since generation (likely verification failed)
        const timeSinceGeneration =
          Date.now() - (otpInfo.expires_at - 2 * 60 * 1000);
        if (timeSinceGeneration > 15 * 1000) {
          // 15 seconds - more aggressive detection
          console.log(
            "🔧 Debug: OTP has been unused for too long, restarting verification flow",
          );
          clearAuthData();
          return false; // Restart the flow
        }

        otpData.value = otpInfo;
        loading.value = false;
        return true;
      } else {
        // Clean up expired data
        clearAuthData();
      }
    } catch (e) {
      console.error("Error parsing stored OTP data:", e);
      clearAuthData();
    }
  }
  return false;
};

// Clear authentication data from localStorage
const clearAuthData = () => {
  localStorage.removeItem("auth_otp");
  localStorage.removeItem("auth_flow");
  localStorage.removeItem("auth_redirect_time");
};

// Load Turnstile script
const loadTurnstile = () => {
  return new Promise((resolve, reject) => {
    if (window.turnstile) {
      resolve();
      return;
    }

    const existingScript = document.querySelector('script[src*="turnstile"]');
    if (existingScript) {
      existingScript.onload = resolve;
      existingScript.onerror = reject;
      return;
    }

    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
    script.async = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
};

// Initialize Turnstile widget
const initializeTurnstile = async () => {
  // Prevent concurrent initialization
  if (isInitializingTurnstile) {
    console.log(
      "🔧 Debug: Turnstile initialization already in progress, skipping",
    );
    return;
  }

  isInitializingTurnstile = true;

  try {
    console.log(
      "🔧 Debug: VITE_TURNSTILE_SITE_KEY =",
      import.meta.env.VITE_TURNSTILE_SITE_KEY,
    );

    // Always cleanup any existing widget first
    cleanupTurnstile();

    // First ensure we're in the right state for turnstile to be rendered
    loading.value = false;
    turnstileToken.value = null;
    otpData.value = null;
    error.value = null;

    await loadTurnstile();

    // Use multiple nextTicks to ensure DOM is fully updated
    await nextTick();
    await nextTick();
    await nextTick();

    // Wait for DOM element to be available with longer timeout and more attempts
    let widgetContainer = null;
    let attempts = 0;
    const maxAttempts = 30; // Further increased attempts
    const waitTime = 300; // Increased wait time

    while (!widgetContainer && attempts < maxAttempts) {
      widgetContainer = document.getElementById("turnstile-widget");
      if (!widgetContainer) {
        console.log(
          `🔧 Debug: Waiting for turnstile-widget container (attempt ${attempts + 1}/${maxAttempts})`,
        );
        // Ensure we're still in the correct state
        if (
          loading.value ||
          turnstileToken.value ||
          otpData.value ||
          error.value
        ) {
          console.log("🔧 Debug: State changed during wait, resetting state");
          loading.value = false;
          turnstileToken.value = null;
          otpData.value = null;
          error.value = null;
          await nextTick();
        }
        await new Promise((resolve) => setTimeout(resolve, waitTime));
        attempts++;
      }
    }

    if (!widgetContainer) {
      console.error("Turnstile widget container not found after waiting");
      error.value =
        "Failed to initialize security verification. Please try again.";
      return;
    }

    // Clear container content to ensure clean state
    widgetContainer.innerHTML = "";

    const siteKey =
      import.meta.env.VITE_TURNSTILE_SITE_KEY || "0x4AAAAAAABVPBtNKmaBqXhw";
    console.log("🔧 Debug: Using site key =", siteKey);

    turnstileWidget = window.turnstile.render(widgetContainer, {
      sitekey: siteKey,
      callback: (token) => {
        console.log("🔧 Debug: Turnstile callback received");
        turnstileToken.value = token;
        loading.value = false;
      },
      "error-callback": (errorCode) => {
        console.error("Turnstile error:", errorCode);
        // Reset initialization flag so retry can work
        isInitializingTurnstile = false;
        error.value = "Security verification failed. Please try again.";
        loading.value = false;
      },
      "expired-callback": () => {
        console.log("🔧 Debug: Turnstile expired");
        // Reset initialization flag so retry can work
        isInitializingTurnstile = false;
        turnstileToken.value = null;
        error.value = "Security verification expired. Please try again.";
      },
      theme: "light",
      size: "normal",
    });

    console.log("🔧 Debug: Turnstile widget created with ID:", turnstileWidget);
  } catch (err) {
    console.error("Failed to load Turnstile:", err);
    error.value = "Failed to load security verification. Please try again.";
  } finally {
    isInitializingTurnstile = false;
  }
};

// Initiate authentication
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
      const expiresAt = Date.now() + 2 * 60 * 1000; // 2 minutes from now
      const otpInfo = {
        otp: data.otp,
        expires_at: expiresAt,
      };
      const flowInfo = {
        status: "pending",
        action: props.action,
        expires_at: Date.now() + 10 * 60 * 1000, // 10 minutes from now
      };

      // Store in localStorage
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

// Copy OTP and redirect
const copyOTPAndRedirect = async () => {
  if (!otpData.value || !redirectUrl.value) return;

  try {
    // Record the time when user leaves for questionnaire
    localStorage.setItem("auth_redirect_time", Date.now().toString());

    // Copy to clipboard
    await navigator.clipboard.writeText(otpData.value.otp);
    copyButtonText.value = "Copied! ✓";

    // Start countdown and redirect
    redirecting.value = true;
    countdown.value = 1;

    countdownInterval = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(countdownInterval);
        // Append OTP as hint parameter
        const url = new URL(redirectUrl.value);
        url.searchParams.set("otp_hint", otpData.value.otp);
        window.location.href = url.toString();
      }
    }, 1000);
  } catch (err) {
    console.error("Failed to copy to clipboard:", err);
    // Fallback: just redirect without clipboard
    setTimeout(() => {
      const url = new URL(redirectUrl.value);
      url.searchParams.set("otp_hint", otpData.value.otp);
      window.location.href = url.toString();
    }, 1000);
  }
};

// Format time remaining
const formatTime = (expiresAt) => {
  const remaining = Math.max(
    0,
    Math.floor((expiresAt - currentTime.value) / 1000),
  );
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

// Get cookie value
const getCookie = (name) => {
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
};

// Reset authentication state
const resetAuth = () => {
  console.log("🔧 Debug: Resetting auth state (try again)");

  // Clear all state
  error.value = null;
  turnstileToken.value = null;
  otpData.value = null;
  redirecting.value = false;
  copyButtonText.value = "Copy Code & Continue";

  // Reset initialization flag to allow retry
  isInitializingTurnstile = false;

  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }

  clearAuthData();

  // Use cleanup function instead of reset to ensure complete removal
  cleanupTurnstile();

  // Set loading state briefly to show user we're working
  loading.value = true;

  // Add delay to ensure cleanup is complete before reinitializing
  setTimeout(async () => {
    await initializeTurnstile();
  }, 300); // Increased delay for error recovery
};

// Component lifecycle
onMounted(async () => {
  // Start time update interval for reactive countdown
  timeUpdateInterval = setInterval(() => {
    currentTime.value = Date.now();
  }, 1000);

  // Check if user just returned from signup or questionnaire
  const urlParams = new URLSearchParams(window.location.search);
  const hasOtpHint = urlParams.has("otp_hint");
  const referrer = document.referrer;
  const isFromQuestionnaire =
    referrer.includes("questionnaire") ||
    referrer.includes("sjtu") ||
    hasOtpHint;

  // If user is on signup, reset_password, or login page and has stored auth data, restart verification flow
  const isOnSignupWithStoredAuth =
    props.action === "signup" && localStorage.getItem("auth_otp");
  const isOnResetPasswordWithStoredAuth =
    props.action === "reset_password" && localStorage.getItem("auth_otp");
  const isOnLoginWithStoredAuth =
    props.action === "login" && localStorage.getItem("auth_otp");

  // If user returned from signup/reset_password/login/questionnaire, always restart verification flow
  if (
    isFromQuestionnaire ||
    isOnSignupWithStoredAuth ||
    isOnResetPasswordWithStoredAuth ||
    isOnLoginWithStoredAuth
  ) {
    console.log(
      "🔧 Debug: Detected",
      isOnSignupWithStoredAuth
        ? "signup page with stored auth data"
        : isOnResetPasswordWithStoredAuth
          ? "reset_password page with stored auth data"
          : isOnLoginWithStoredAuth
            ? "login page with stored auth data"
            : "return from questionnaire",
      "- restarting verification flow",
    );
    clearAuthData();
    // Don't set loading.value = true, let initializeTurnstile handle the state
    await nextTick();
    await initializeTurnstile();
    return;
  }

  // Add visibility change listener to detect when user returns from questionnaire
  const handleVisibilityChange = () => {
    // Only check when page becomes visible
    if (document.visibilityState === "visible") {
      // Check if we have an OTP that's been around for a while
      const storedOTP = localStorage.getItem("auth_otp");
      const redirectTime = localStorage.getItem("auth_redirect_time");

      if (storedOTP) {
        try {
          const otpInfo = JSON.parse(storedOTP);
          const now = Date.now();

          // Check time since OTP generation
          const timeSinceGeneration =
            now - (otpInfo.expires_at - 2 * 60 * 1000);

          // If user left for questionnaire, check time since redirect
          if (redirectTime) {
            const timeSinceRedirect = now - parseInt(redirectTime);
            // If user returned within 60 seconds, likely verification failed
            if (timeSinceRedirect < 60 * 1000 && timeSinceRedirect > 5 * 1000) {
              console.log(
                "🔧 Debug: User returned quickly from questionnaire, likely verification failed",
              );
              clearAuthData();
              localStorage.removeItem("auth_redirect_time");
              otpData.value = null;
              // Don't set loading.value = true, let initializeTurnstile handle the state
              setTimeout(async () => {
                await initializeTurnstile();
              }, 100);
              return;
            }
          }

          // If OTP exists for more than 30 seconds when user returns, likely verification failed
          if (timeSinceGeneration > 30 * 1000) {
            console.log(
              "🔧 Debug: OTP has been unused for too long, restarting verification flow",
            );
            clearAuthData();
            localStorage.removeItem("auth_redirect_time");
            otpData.value = null;
            // Don't set loading.value = true, let initializeTurnstile handle the state
            setTimeout(async () => {
              await initializeTurnstile();
            }, 100);
          }
        } catch (e) {
          console.error("Error checking OTP on visibility change:", e);
        }
      }
    }
  };

  document.addEventListener("visibilitychange", handleVisibilityChange);

  // Store the handler for cleanup
  window._authVisibilityHandler = handleVisibilityChange;

  // Check for existing valid OTP first
  if (!checkExistingOTP()) {
    // No valid OTP, set loading to false first to render the turnstile container
    loading.value = false;
    await nextTick();
    await initializeTurnstile();
  } else {
    // OTP exists, just show it
    loading.value = false;
  }
});

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
  }

  // Use cleanup function for consistent turnstile cleanup
  cleanupTurnstile();

  // Clean up visibility change event listener
  if (window._authVisibilityHandler) {
    document.removeEventListener(
      "visibilitychange",
      window._authVisibilityHandler,
    );
    delete window._authVisibilityHandler;
  }
});
</script>

<style scoped>
.auth-initiate {
  max-width: 100%;
}
</style>
