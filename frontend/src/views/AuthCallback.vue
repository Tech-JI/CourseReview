<template>
  <div
    class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8"
  >
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Verifying Authentication
        </h2>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center">
        <div
          class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"
        ></div>
        <p class="mt-4 text-sm text-gray-500">
          Please wait while we verify your authentication...
        </p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="rounded-md bg-red-50 p-4">
        <div class="flex">
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">
              Verification Failed
            </h3>
            <div class="mt-2 text-sm text-red-700">
              <p>{{ error }}</p>
            </div>
            <div class="mt-4 flex space-x-3">
              <button
                @click="retryVerification"
                type="button"
                class="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2"
              >
                Retry Verification
              </button>
              <router-link
                :to="getReturnPath()"
                class="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 inline-block"
              >
                Return to {{ getActionDisplayName() }}
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Success State (should not be visible as we redirect immediately) -->
      <div v-else-if="success" class="rounded-md bg-green-50 p-4">
        <div class="flex">
          <div class="ml-3">
            <h3 class="text-sm font-medium text-green-800">
              Verification Successful
            </h3>
            <div class="mt-2 text-sm text-green-700">
              <p>Authentication verified successfully. Redirecting...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const error = ref(null);
const success = ref(false);
const parsedParams = ref({});

// Parse query parameters from URL
const parseUrlParams = () => {
  const { account, answer_id, action } = route.query;

  if (!account || !answer_id || !action) {
    error.value =
      "Missing required parameters. Please try the authentication process again.";
    loading.value = false;
    return null;
  }

  // Validate action parameter - only allow the three valid actions
  const validActions = ["signup", "login", "reset_password"];
  if (!validActions.includes(action)) {
    error.value =
      "Invalid action parameter. Please try the authentication process again.";
    loading.value = false;
    return null;
  }

  return { account, answer_id, action };
};

// Call backend verification API
const verifyAuthentication = async (params) => {
  try {
    const response = await fetch("/api/auth/verify/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // Include HttpOnly cookies
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail ||
          errorData.error ||
          `Server returned ${response.status}`,
      );
    }

    const data = await response.json();
    return data;
  } catch (err) {
    console.error("Verification API error:", err);
    throw err;
  }
};

// Store verification result in localStorage
const storeVerificationResult = (action, expires_at, account) => {
  const authFlowState = {
    status: "verified",
    action: action,
    account: account, // Add account information
    expires_at: expires_at,
    verified_at: new Date().toISOString(),
  };

  // Try multiple storage methods
  const stateString = JSON.stringify(authFlowState);
  localStorage.setItem("auth_flow", stateString);
  sessionStorage.setItem("auth_flow", stateString);
  sessionStorage.setItem("auth_verification_data", stateString); // Backup key

  // Debug: Verify what was actually stored
  const storedState = localStorage.getItem("auth_flow");
  const sessionState = sessionStorage.getItem("auth_flow");
  try {
    const parsedState = JSON.parse(storedState);
  } catch (e) {
    console.error("Failed to parse stored state:", e);
  }
};

// Get redirect path based on action
const getRedirectPath = (action) => {
  switch (action) {
    case "login":
      return "/"; // Redirect to homepage for login
    case "signup":
      return "/accounts/signup"; // Redirect back to accounts signup page
    case "reset_password":
      return "/accounts/reset"; // Redirect back to accounts reset password page
    default:
      return "/"; // Fallback to homepage
  }
};

// Get return path for error state
const getReturnPath = () => {
  const action = parsedParams.value.action;
  switch (action) {
    case "signup":
      return "/accounts/signup";
    case "login":
      return "/accounts/login";
    case "reset_password":
      return "/accounts/reset";
    default:
      return "/";
  }
};

// Get display name for action
const getActionDisplayName = () => {
  const action = parsedParams.value.action;
  switch (action) {
    case "signup":
      return "Sign Up";
    case "login":
      return "Login";
    case "reset_password":
      return "Reset Password";
    default:
      return "Home";
  }
};

// Retry verification
const retryVerification = () => {
  error.value = null;
  loading.value = true;
  performVerification();
};

// Main verification logic
const performVerification = async () => {
  try {
    const params = parseUrlParams();
    if (!params) {
      return; // Error already set in parseUrlParams
    }

    parsedParams.value = params;

    const result = await verifyAuthentication(params);

    // Store the verification result
    storeVerificationResult(result.action, result.expires_at, params.account);

    success.value = true;
    loading.value = false;

    // Redirect based on action
    const redirectPath = getRedirectPath(result.action);

    // Small delay to show success state, then redirect
    setTimeout(() => {
      // Debug: Final check before redirect
      const finalCheck = localStorage.getItem("auth_flow");
      const sessionCheck = sessionStorage.getItem("auth_flow");

      // Also pass verification state in URL as backup
      const urlParams = new URLSearchParams({
        verified: "true",
        account: params.account,
        action: result.action,
        expires_at: result.expires_at,
        from_callback: "true",
      });

      const redirectWithParams = `${redirectPath}?${urlParams.toString()}`;

      router.push(redirectWithParams);
    }, 500);
  } catch (err) {
    console.error("Verification failed:", err);
    error.value =
      err.message || "An unexpected error occurred during verification.";
    loading.value = false;
  }
};

// Component lifecycle
onMounted(() => {
  performVerification();
});
</script>
