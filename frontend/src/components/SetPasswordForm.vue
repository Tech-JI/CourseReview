<template>
  <div class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10">
    <form class="space-y-6" @submit.prevent="handleSubmit">
      <div>
        <h3 class="text-lg/7 font-semibold text-gray-900 text-center">
          {{ formTitle }}
        </h3>
        <p class="mt-1 text-sm/6 text-gray-600 text-center">
          {{ formDescription }}
        </p>
      </div>

      <div>
        <label for="password" class="block text-sm/6 font-medium text-gray-900">
          {{ action === "reset_password" ? "New Password" : "Password" }}
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
            class="absolute inset-y-0 right-0 pr-3 flex items-center"
            :disabled="isLoading"
            @click="showPassword = !showPassword"
          >
            <Icon
              :name="showPassword ? 'eye-closed' : 'eye-open'"
              class="text-gray-400"
            />
          </button>
        </div>
        <p v-if="errors.password" class="mt-2 text-sm/6 text-red-600">
          {{ errors.password }}
        </p>

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
            class="absolute inset-y-0 right-0 pr-3 flex items-center"
            :disabled="isLoading"
            @click="showConfirmPassword = !showConfirmPassword"
          >
            <Icon
              :name="showConfirmPassword ? 'eye-closed' : 'eye-open'"
              class="text-gray-400"
            />
          </button>
        </div>
        <p v-if="errors.confirmPassword" class="mt-2 text-sm/6 text-red-600">
          {{ errors.confirmPassword }}
        </p>
      </div>

      <div v-if="submitError" class="rounded-lg bg-red-50 p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <Icon name="x" class="text-red-400" />
          </div>
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-red-800">
              {{ submitError }}
            </h3>
          </div>
        </div>
      </div>

      <div v-if="submitSuccess" class="rounded-lg bg-green-50 p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <Icon name="check-circle" class="text-green-400" />
          </div>
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-green-800">
              {{ submitSuccess }}
            </h3>
          </div>
        </div>
      </div>

      <div>
        <button
          type="submit"
          :disabled="isLoading || !isFormValid"
          class="w-full flex justify-center py-2 px-3 border border-transparent rounded-md shadow-sm text-sm/6 font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition duration-150 ease-in-out"
        >
          <Icon v-if="isLoading" name="loading" class="-ml-1 mr-3 text-white" />
          {{ isLoading ? "Processing..." : submitButtonText }}
        </button>
      </div>

      <div v-if="showBackButton" class="text-center">
        <button
          type="button"
          class="text-sm/6 text-indigo-600 hover:text-indigo-500 transition duration-150 ease-in-out"
          :disabled="isLoading"
          @click="$emit('back')"
        >
          Back
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import { ref, computed, watch } from "vue";
import { getAuthState } from "../utils/auth";
import { getCookie } from "../utils/cookies";
import {
  calculatePasswordStrength,
  getPasswordStrengthText,
  getPasswordStrengthColor,
  getPasswordStrengthPercentage,
  validatePassword,
  validatePasswordConfirmation,
} from "../utils/validation";
import Icon from "./Icon.vue";

export default {
  name: "SetPasswordForm",
  components: {
    Icon,
  },
  props: {
    action: {
      type: String,
      required: true,
      validator: (value) => ["signup", "reset_password"].includes(value),
    },
    showBackButton: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["submit", "success", "error", "back"],
  setup(props, { emit }) {
    const isLoading = ref(false);
    const showPassword = ref(false);
    const showConfirmPassword = ref(false);
    const submitError = ref("");
    const submitSuccess = ref("");

    const formData = ref({
      password: "",
      confirmPassword: "",
    });

    const errors = ref({
      password: "",
      confirmPassword: "",
    });

    const formTitle = computed(() => {
      return props.action === "signup"
        ? "Set Account Password"
        : "Reset Password";
    });

    const formDescription = computed(() => {
      return props.action === "signup"
        ? "Set a secure password for your account"
        : "Enter your new password";
    });

    const submitButtonText = computed(() => {
      return props.action === "signup"
        ? "Complete Registration"
        : "Reset Password";
    });

    const passwordStrength = computed(() => {
      return calculatePasswordStrength(formData.value.password);
    });

    const passwordStrengthPercentage = computed(() => {
      return getPasswordStrengthPercentage(passwordStrength.value);
    });

    const passwordStrengthText = computed(() => {
      return getPasswordStrengthText(passwordStrength.value);
    });

    const passwordStrengthColor = computed(() => {
      return getPasswordStrengthColor(passwordStrength.value);
    });

    const isFormValid = computed(() => {
      return (
        formData.value.password &&
        formData.value.confirmPassword &&
        !errors.value.password &&
        !errors.value.confirmPassword
      );
    });

    function validatePasswordLocal() {
      const result = validatePassword(formData.value.password);
      errors.value.password = result.errors[0] || "";

      if (formData.value.confirmPassword) {
        validateConfirmPasswordLocal();
      }
    }

    function validateConfirmPasswordLocal() {
      const result = validatePasswordConfirmation(
        formData.value.password,
        formData.value.confirmPassword,
      );
      errors.value.confirmPassword = result.errors[0] || "";
    }

    function validateForm() {
      validatePasswordLocal();
      validateConfirmPasswordLocal();

      return isFormValid.value;
    }

    function getAuthStateLocal() {
      return getAuthState();
    }

    function getCsrfToken() {
      return getCookie("csrftoken");
    }

    async function handleSubmit() {
      submitError.value = "";
      submitSuccess.value = "";

      if (!validateForm()) {
        return;
      }

      isLoading.value = true;

      try {
        const authState = getAuthStateLocal();
        if (!authState) {
          throw new Error("Authentication state not found, please start over");
        }

        if (authState.status !== "verified") {
          throw new Error("Please complete identity verification first");
        }

        const requestData = {
          password: formData.value.password,
        };

        const endpoint =
          props.action === "signup"
            ? "/api/auth/signup/"
            : "/api/auth/password/";

        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          credentials: "include",
          body: JSON.stringify(requestData),
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.error || `Server error (${response.status})`);
        }

        const data = await response.json();

        const successMessage =
          props.action === "signup"
            ? "Registration successful! Welcome aboard"
            : "Password reset successful!";

        submitSuccess.value = successMessage;

        // Delete OTP and auth flow state from localStorage on success
        localStorage.removeItem("auth_otp");
        localStorage.removeItem("auth_flow");
        localStorage.removeItem("auth_redirect_time");

        emit("success", { action: props.action, data });

        // Redirect to / after success
        setTimeout(() => {
          window.location.href = "/";
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

    return {
      action: props.action, // Expose action to template
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
      validatePassword: validatePasswordLocal,
      validateConfirmPassword: validateConfirmPasswordLocal,
      handleSubmit,
    };
  },
};
</script>

<style scoped>
input:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.password-strength-bar {
  transition:
    width 0.3s ease-in-out,
    background-color 0.3s ease-in-out;
}
</style>
