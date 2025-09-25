<template>
  <div
    class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8"
  >
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="text-center">
        <h2
          class="mt-6 text-center text-2xl/9 font-bold tracking-tight text-gray-900"
        >
          Create your account
        </h2>
        <p class="mt-2 text-sm text-gray-600">
          Join JI Course Review community
        </p>
        <p class="mt-2 text-sm text-gray-600">
          Already have an account?
          <router-link
            to="/accounts/login"
            class="font-semibold text-indigo-600 hover:text-indigo-500"
          >
            Sign in
          </router-link>
        </p>
      </div>
    </div>

    <div class="mt-10 sm:mx-auto sm:w-full sm:max-w-[480px]">
      <!-- If auth flow is verified, show password form -->
      <SetPasswordForm v-if="showPasswordForm" action="signup" />
      <!-- Otherwise show auth initiate -->
      <AuthInitiate v-else action="signup" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import AuthInitiate from "../components/AuthInitiate.vue";
import SetPasswordForm from "../components/SetPasswordForm.vue";

const showPasswordForm = ref(false);

const checkAuthState = () => {
  try {
    const authFlow = localStorage.getItem("auth_flow");

    if (authFlow) {
      const flowData = JSON.parse(authFlow);

      // Check if verified, correct action, and not expired
      const isVerified = flowData.status === "verified";
      const isSignupAction = flowData.action === "signup";
      const hasExpiresAt = !!flowData.expires_at;
      const isNotExpired =
        flowData.expires_at && Date.now() < parseInt(flowData.expires_at);

      if (isVerified && isSignupAction && hasExpiresAt && isNotExpired) {
        showPasswordForm.value = true;
        return;
      }
    }

    showPasswordForm.value = false;
  } catch (e) {
    console.error("Error checking auth state:", e);
    showPasswordForm.value = false;
  }
};

onMounted(() => {
  // Check URL parameters first (from AuthCallback redirect)
  const urlParams = new URLSearchParams(window.location.search);
  const verified = urlParams.get("verified");
  const action = urlParams.get("action");
  const fromCallback = urlParams.get("from_callback");

  if (verified === "true" && action === "signup" && fromCallback === "true") {
    showPasswordForm.value = true;
    return;
  }

  // Also check for the case where from_callback is not present but we have verification
  if (verified === "true" && action === "signup") {
    showPasswordForm.value = true;
    return;
  }

  // Then check localStorage
  checkAuthState();
});
</script>
