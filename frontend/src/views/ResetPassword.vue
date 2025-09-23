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
            >back to sign in</router-link
          >
        </p>
      </div>
    </div>

    <AuthFlow
      action="reset_password"
      password-label="Set new password"
      set-password-mode="reset"
      success-title="Password reset successful!"
      success-message="Your password has been reset successfully. You can now sign in with your new password."
      success-button-text="Sign in now"
      help-title="Password Reset Instructions"
      :help-items="[
        'First, verify your identity through SJTU authentication',
        'After successful verification, you can set a new password',
        'Ensure your new password is secure (contains letters and numbers, at least 12 characters)',
        'Keep your new password safe after resetting',
      ]"
    />
  </div>
</template>

<script>
import AuthFlow from "../components/AuthFlow.vue";

export default {
  name: "ResetPassword",
  components: { AuthFlow },
};
</script>

<style scoped></style>
