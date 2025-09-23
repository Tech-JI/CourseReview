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

    <AuthFlow
      action="signup"
      password-label="Set your password"
      set-password-mode="signup"
      success-title="Registration successful!"
      success-message="Welcome to CourseReview! Your account has been created successfully."
      success-button-text="Sign in now"
      help-title=""
      :help-items="[]"
    />
  </div>
</template>

<script>
import { ref, onMounted } from "vue";
import AuthFlow from "../components/AuthFlow.vue";

export default {
  name: "Signup",
  components: { AuthFlow },
  setup() {
    const accountForm = ref({ account: "" });

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

    onMounted(() => {
      const authState = getAuthState();
      if (
        authState &&
        authState.action === "signup" &&
        authState.status === "verified"
      ) {
        accountForm.value.account = authState.account || "";
      }
    });

    return { accountForm };
  },
};
</script>

<style scoped></style>
