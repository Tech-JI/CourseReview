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

      <div v-if="loading" class="text-center">
        <div
          class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"
        ></div>
        <p class="mt-4 text-sm text-gray-500">
          Please wait while we verify your authentication...
        </p>
      </div>

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
                type="button"
                class="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2"
                @click="retryVerification"
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

const parseUrlParams = () => {
  const { account, answer_id, action } = route.query;

  if (!account || !answer_id || !action) {
    error.value =
      "Missing required parameters. Please try the authentication process again.";
    loading.value = false;
    return null;
  }

  const validActions = ["signup", "login", "reset_password"];
  if (!validActions.includes(action)) {
    error.value =
      "Invalid action parameter. Please try the authentication process again.";
    loading.value = false;
    return null;
  }

  return { account, answer_id, action };
};

const verifyAuthentication = async (params) => {
  try {
    const response = await fetch("/api/auth/verify/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
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

const storeVerificationResult = (action, expires_at, account) => {
  const authFlowState = {
    status: "verified",
    action: action,
    account: account,
    expires_at: expires_at,
    verified_at: new Date().toISOString(),
  };

  const stateString = JSON.stringify(authFlowState);
  localStorage.setItem("auth_flow", stateString);
  sessionStorage.setItem("auth_flow", stateString);
  sessionStorage.setItem("auth_verification_data", stateString);
};

const getRedirectPath = (action) => {
  switch (action) {
    case "login":
      return "/";
    case "signup":
      return "/signup";
    case "reset_password":
      return "/reset";
    default:
      return "/";
  }
};

const getReturnPath = () => {
  const action = parsedParams.value.action;
  switch (action) {
    case "signup":
      return "/signup";
    case "login":
      return "/login";
    case "reset_password":
      return "/reset";
    default:
      return "/";
  }
};

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

const retryVerification = () => {
  error.value = null;
  loading.value = true;
  performVerification();
};

const performVerification = async () => {
  try {
    const params = parseUrlParams();
    if (!params) {
      return;
    }

    parsedParams.value = params;

    const result = await verifyAuthentication(params);

    storeVerificationResult(result.action, result.expires_at, params.account);

    success.value = true;
    loading.value = false;

    try {
      if (result.action === "login") {
        window.dispatchEvent(new CustomEvent("auth-state-changed"));
      }
    } catch (e) {
      console.warn("Could not dispatch auth-state-changed event:", e);
    }
    const redirectPath = getRedirectPath(result.action);

    setTimeout(() => {
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

onMounted(() => {
  performVerification();
});
</script>
