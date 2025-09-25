<template>
  <!-- Error Toast -->
  <div
    v-if="showErrorToast"
    class="fixed bottom-4 right-4 max-w-sm bg-red-50 border border-red-200 rounded-lg shadow-lg z-50 transform transition-all duration-300"
    :class="
      errorToastVisible
        ? 'translate-y-0 opacity-100'
        : 'translate-y-2 opacity-0'
    "
  >
    <div class="p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <Icon name="x" size="sm" class="text-red-400" />
        </div>
        <div class="ml-3">
          <p class="text-sm/6 font-medium text-red-800">
            {{ errorToastMessage }}
          </p>
        </div>
        <div class="ml-auto pl-3">
          <div class="-mx-1.5 -my-1.5">
            <button
              class="inline-flex bg-red-50 rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
              @click="hideError"
            >
              <Icon name="x" size="xs" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Success Toast -->
  <div
    v-if="showSuccessToast"
    class="fixed bottom-4 right-4 max-w-sm bg-green-50 border border-green-200 rounded-lg shadow-lg z-50 transform transition-all duration-300"
    :class="
      successToastVisible
        ? 'translate-y-0 opacity-100'
        : 'translate-y-2 opacity-0'
    "
  >
    <div class="p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <Icon name="check-circle" size="sm" class="text-green-400" />
        </div>
        <div class="ml-3">
          <p class="text-sm/6 font-medium text-green-800">
            {{ successToastMessage }}
          </p>
        </div>
        <div class="ml-auto pl-3">
          <div class="-mx-1.5 -my-1.5">
            <button
              class="inline-flex bg-green-50 rounded-md p-1.5 text-green-500 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-green-50 focus:ring-green-600"
              @click="hideSuccess"
            >
              <Icon name="x" size="xs" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onUnmounted } from "vue";
import { useNotifications } from "../composables/useNotifications";
import Icon from "./Icon.vue";

const {
  showErrorToast,
  errorToastVisible,
  errorToastMessage,
  showSuccessToast,
  successToastVisible,
  successToastMessage,
  showError,
  showSuccess,
  hideError,
  hideSuccess,
  cleanup,
} = useNotifications();

// Expose the notification methods to parent
defineExpose({
  showError,
  showSuccess,
  hideError,
  hideSuccess,
});

onUnmounted(() => {
  cleanup();
});
</script>
