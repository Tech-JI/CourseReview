<template>
  <div class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10">
    <form @submit.prevent="handleSubmit" class="space-y-6">
      <!-- Title -->
      <div>
        <h3 class="text-lg/7 font-semibold text-gray-900 text-center">
          {{ formTitle }}
        </h3>
        <p class="mt-1 text-sm/6 text-gray-600 text-center">
          {{ formDescription }}
        </p>
      </div>

      <!-- Student ID (for signup only) -->
      <div v-if="mode === 'signup'">
        <label
          for="student-id"
          class="block text-sm/6 font-medium text-gray-900"
        >
          Student ID
        </label>
        <div class="mt-2">
          <input
            id="student-id"
            v-model="formData.studentId"
            type="text"
            required
            maxlength="20"
            class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
            :class="{
              'outline-red-300 focus:outline-red-600': errors.studentId,
            }"
            placeholder="Enter your student ID"
            :disabled="isLoading"
          />
          <p v-if="errors.studentId" class="mt-2 text-sm/6 text-red-600">
            {{ errors.studentId }}
          </p>
        </div>
      </div>

      <!-- Email (for signup only) -->
      <div v-if="mode === 'signup'">
        <label for="email" class="block text-sm/6 font-medium text-gray-900">
          Email Address
        </label>
        <div class="mt-2">
          <input
            id="email"
            v-model="formData.email"
            type="email"
            required
            maxlength="255"
            class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
            :class="{
              'outline-red-300 focus:outline-red-600': errors.email,
            }"
            placeholder="Enter your email address"
            :disabled="isLoading"
          />
          <p v-if="errors.email" class="mt-2 text-sm/6 text-red-600">
            {{ errors.email }}
          </p>
        </div>
      </div>

      <!-- Password -->
      <div>
        <label for="password" class="block text-sm/6 font-medium text-gray-900">
          {{ mode === "reset" ? "New Password" : "Password" }}
        </label>
        <div class="mt-2 relative">
          <input
            id="password"
            v-model="formData.password"
            :type="showPassword ? 'text' : 'password'"
            required
            minlength="8"
            maxlength="128"
            class="block w-full rounded-md bg-white px-3 py-1.5 pr-10 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
            :class="{
              'outline-red-300 focus:outline-red-600': errors.password,
            }"
            placeholder="Enter password (at least 12 characters)"
            :disabled="isLoading"
            @input="validatePassword"
          />
          <button
            type="button"
            @click="showPassword = !showPassword"
            class="absolute inset-y-0 right-0 pr-3 flex items-center"
            :disabled="isLoading"
          >
            <svg
              v-if="showPassword"
              class="size-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L8.464 8.464M9.878 9.878l-7.071 7.071M21.536 16.536L8.464 3.464"
              ></path>
            </svg>
            <svg
              v-else
              class="size-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              ></path>
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              ></path>
            </svg>
          </button>
        </div>
        <p v-if="errors.password" class="mt-2 text-sm/6 text-red-600">
          {{ errors.password }}
        </p>

        <!-- Password strength indicator -->
        <div v-if="formData.password" class="mt-2">
          <div class="flex justify-between items-center mb-1">
            <span class="text-xs/5 text-gray-600">Password Strength</span>
            <span class="text-xs/5" :class="passwordStrengthColor">{{
              passwordStrengthText
            }}</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-1.5">
            <div
              class="h-1.5 rounded-full transition-all duration-300"
              :class="passwordStrengthColor"
              :style="{ width: passwordStrengthPercentage + '%' }"
            ></div>
          </div>
        </div>
      </div>

      <!-- Confirm Password -->
      <div>
        <label
          for="confirm-password"
          class="block text-sm/6 font-medium text-gray-900"
        >
          Confirm Password
        </label>
        <div class="mt-2 relative">
          <input
            id="confirm-password"
            v-model="formData.confirmPassword"
            :type="showConfirmPassword ? 'text' : 'password'"
            required
            maxlength="128"
            class="block w-full rounded-md bg-white px-3 py-1.5 pr-10 text-base text-gray-900 outline outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
            :class="{
              'outline-red-300 focus:outline-red-600': errors.confirmPassword,
            }"
            placeholder="Enter password again"
            :disabled="isLoading"
            @input="validateConfirmPassword"
          />
          <button
            type="button"
            @click="showConfirmPassword = !showConfirmPassword"
            class="absolute inset-y-0 right-0 pr-3 flex items-center"
            :disabled="isLoading"
          >
            <svg
              v-if="showConfirmPassword"
              class="size-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L8.464 8.464M9.878 9.878l-7.071 7.071M21.536 16.536L8.464 3.464"
              ></path>
            </svg>
            <svg
              v-else
              class="size-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              ></path>
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              ></path>
            </svg>
          </button>
        </div>
        <p v-if="errors.confirmPassword" class="mt-2 text-sm/6 text-red-600">
          {{ errors.confirmPassword }}
        </p>
      </div>

      <!-- Error message -->
      <div v-if="submitError" class="rounded-lg bg-red-50 p-4">
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
            <h3 class="text-sm/6 font-medium text-red-800">
              {{ submitError }}
            </h3>
          </div>
        </div>
      </div>

      <!-- Success message -->
      <div v-if="submitSuccess" class="rounded-lg bg-green-50 p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg
              class="size-5 text-green-400"
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
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-green-800">
              {{ submitSuccess }}
            </h3>
          </div>
        </div>
      </div>

      <!-- Submit button -->
      <div>
        <button
          type="submit"
          :disabled="isLoading || !isFormValid"
          class="w-full flex justify-center py-2 px-3 border border-transparent rounded-md shadow-sm text-sm/6 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition duration-150 ease-in-out"
        >
          <svg
            v-if="isLoading"
            class="animate-spin -ml-1 mr-3 size-5 text-white"
            fill="none"
            stroke="currentColor"
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
          {{ isLoading ? "Processing..." : submitButtonText }}
        </button>
      </div>

      <!-- Additional actions -->
      <div v-if="showBackButton" class="text-center">
        <button
          type="button"
          @click="$emit('back')"
          class="text-sm/6 text-indigo-600 hover:text-indigo-500 transition duration-150 ease-in-out"
          :disabled="isLoading"
        >
          Back
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import { ref, computed, watch } from "vue";

export default {
  name: "SetPasswordForm",
  props: {
    mode: {
      type: String,
      required: true,
      validator: (value) => ["signup", "reset"].includes(value),
    },
    showBackButton: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["submit", "success", "error", "back"],
  setup(props, { emit }) {
    // Reactive state
    const isLoading = ref(false);
    const showPassword = ref(false);
    const showConfirmPassword = ref(false);
    const submitError = ref("");
    const submitSuccess = ref("");

    const formData = ref({
      studentId: "",
      email: "",
      password: "",
      confirmPassword: "",
    });

    const errors = ref({
      studentId: "",
      email: "",
      password: "",
      confirmPassword: "",
    });

    // Computed properties
    const formTitle = computed(() => {
      return props.mode === "signup"
        ? "Set Account Password"
        : "Reset Password";
    });

    const formDescription = computed(() => {
      return props.mode === "signup"
        ? "Please provide your basic information and set a password"
        : "Enter your new password";
    });

    const submitButtonText = computed(() => {
      return props.mode === "signup"
        ? "Complete Registration"
        : "Reset Password";
    });

    const passwordStrength = computed(() => {
      const password = formData.value.password;
      if (!password) return 0;

      let score = 0;
      // Length check - 12 characters is now the baseline
      if (password.length < 10) return 1;
      if (password.length >= 12) score += 1;
      if (password.length >= 16) score += 1;

      // Character variety
      if (/[a-z]/.test(password)) score += 1;
      if (/[A-Z]/.test(password)) score += 1;
      if (/[0-9]/.test(password)) score += 1;
      if (/[^A-Za-z0-9]/.test(password)) score += 1;

      return Math.min(score, 5);
    });

    const passwordStrengthPercentage = computed(() => {
      return (passwordStrength.value / 5) * 100;
    });

    const passwordStrengthText = computed(() => {
      const strength = passwordStrength.value;
      if (strength <= 1) return "Weak";
      if (strength <= 2) return "Fair";
      if (strength <= 3) return "Good";
      if (strength <= 4) return "Strong";
      return "Very Strong";
    });

    const passwordStrengthColor = computed(() => {
      const strength = passwordStrength.value;
      if (strength <= 1) return "text-red-600 bg-red-600";
      if (strength <= 2) return "text-orange-600 bg-orange-600";
      if (strength <= 3) return "text-yellow-600 bg-yellow-600";
      if (strength <= 4) return "text-blue-600 bg-blue-600";
      return "text-green-600 bg-green-600";
    });

    const isFormValid = computed(() => {
      const baseValid =
        formData.value.password &&
        formData.value.confirmPassword &&
        !errors.value.password &&
        !errors.value.confirmPassword;

      if (props.mode === "signup") {
        return (
          baseValid &&
          formData.value.studentId &&
          formData.value.email &&
          !errors.value.studentId &&
          !errors.value.email
        );
      }

      return baseValid;
    });

    // Validation functions
    function validateStudentId() {
      const studentId = formData.value.studentId.trim();
      if (!studentId) {
        errors.value.studentId = "Please enter your student ID";
      } else if (!/^[A-Za-z0-9]+$/.test(studentId)) {
        errors.value.studentId =
          "Student ID can only contain letters and numbers";
      } else if (studentId.length < 2 || studentId.length > 20) {
        errors.value.studentId = "Student ID should be 2-20 characters long";
      } else {
        errors.value.studentId = "";
      }
    }

    function validateEmail() {
      const email = formData.value.email.trim();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!email) {
        errors.value.email = "Please enter your email address";
      } else if (!emailRegex.test(email)) {
        errors.value.email = "Please enter a valid email address";
      } else if (email.length > 255) {
        errors.value.email = "Email address is too long";
      } else {
        errors.value.email = "";
      }
    }

    function validatePassword() {
      const password = formData.value.password;

      if (!password) {
        errors.value.password = "Please enter a password";
      } else if (password.length < 10) {
        errors.value.password = "Password must be at least 10 characters";
      } else if (password.length > 32) {
        errors.value.password = "Password cannot exceed 32 characters";
      } else if (!/(?=.*[a-zA-Z])(?=.*[0-9])/.test(password)) {
        errors.value.password =
          "Password must contain both letters and numbers";
      } else {
        errors.value.password = "";
      }

      // Also validate confirm password if it exists
      if (formData.value.confirmPassword) {
        validateConfirmPassword();
      }
    }

    function validateConfirmPassword() {
      const password = formData.value.password;
      const confirmPassword = formData.value.confirmPassword;

      if (!confirmPassword) {
        errors.value.confirmPassword = "Please confirm your password";
      } else if (password !== confirmPassword) {
        errors.value.confirmPassword = "Passwords do not match";
      } else {
        errors.value.confirmPassword = "";
      }
    }

    function validateForm() {
      if (props.mode === "signup") {
        validateStudentId();
        validateEmail();
      }
      validatePassword();
      validateConfirmPassword();

      return isFormValid.value;
    }

    // Helper functions
    function getAuthState() {
      try {
        // Check URL parameters first (most reliable method)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has("verified") && urlParams.get("verified") === "true") {
          const account = urlParams.get("account");
          const action = urlParams.get("action");
          const expires_at = urlParams.get("expires_at");

          if (account && action) {
            return {
              status: "verified",
              action: action,
              account: account,
              expires_at: expires_at,
              source: "url",
            };
          }
        }

        // Check sessionStorage
        const sessionData = sessionStorage.getItem("auth_flow");
        if (sessionData) {
          const parsed = JSON.parse(sessionData);
          return { ...parsed, source: "sessionStorage" };
        }

        // Check localStorage
        const localData = localStorage.getItem("auth_flow");
        if (localData) {
          const parsed = JSON.parse(localData);
          return { ...parsed, source: "localStorage" };
        }

        return null;
      } catch (error) {
        console.error("Error getting auth state:", error);
        return null;
      }
    }

    function getCsrfToken() {
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        const [name, value] = cookie.trim().split("=");
        if (name === "csrftoken") {
          return value;
        }
      }
      return "";
    }

    async function handleSubmit() {
      // Clear previous messages
      submitError.value = "";
      submitSuccess.value = "";

      // Validate form
      if (!validateForm()) {
        return;
      }

      isLoading.value = true;

      try {
        // Get auth state using the new multi-source approach
        const authState = getAuthState();
        if (!authState) {
          throw new Error("Authentication state not found, please start over");
        }

        if (authState.status !== "verified") {
          throw new Error("Please complete identity verification first");
        }

        // Prepare request data for new auth system
        const requestData = {
          password: formData.value.password,
        };

        // Choose API endpoint based on mode
        const endpoint =
          props.mode === "signup" ? "/api/auth/signup/" : "/api/auth/password/";

        // Make API request
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          credentials: "include",
          body: JSON.stringify(requestData),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || `Server error (${response.status})`);
        }

        // Handle success
        const successMessage =
          props.mode === "signup"
            ? "Registration successful! Welcome aboard"
            : "Password reset successful!";

        submitSuccess.value = successMessage;

        // Clear auth state
        localStorage.removeItem("authState");

        // Emit success event
        emit("success", { mode: props.mode, data });

        // Clear form after a delay
        setTimeout(() => {
          formData.value = {
            studentId: "",
            email: "",
            password: "",
            confirmPassword: "",
          };
        }, 2000);
      } catch (error) {
        console.error("Submit failed:", error);
        submitError.value =
          error.message || "Operation failed, please try again";
        emit("error", error);
      } finally {
        isLoading.value = false;
      }
    }

    // Watchers for real-time validation
    watch(() => formData.value.studentId, validateStudentId);
    watch(() => formData.value.email, validateEmail);

    return {
      formData,
      errors,
      isLoading,
      showPassword,
      showConfirmPassword,
      submitError,
      submitSuccess,
      formTitle,
      formDescription,
      submitButtonText,
      passwordStrength,
      passwordStrengthPercentage,
      passwordStrengthText,
      passwordStrengthColor,
      isFormValid,
      validatePassword,
      validateConfirmPassword,
      handleSubmit,
    };
  },
};
</script>

<style scoped>
/* Custom focus styles for better accessibility */
input:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Smooth transitions for validation states */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

/* Custom animation for password strength bar */
.password-strength-bar {
  transition:
    width 0.3s ease-in-out,
    background-color 0.3s ease-in-out;
}
</style>
