import { ref } from "vue";

// Global state for notifications (singleton pattern)
const showErrorToast = ref(false);
const errorToastVisible = ref(false);
const errorToastMessage = ref("");
const showSuccessToast = ref(false);
const successToastVisible = ref(false);
const successToastMessage = ref("");

let errorToastTimer = null;
let successToastTimer = null;

/**
 * Composable for managing UI notifications (toasts/alerts)
 * Uses singleton pattern to ensure consistent state across components
 */
export function useNotifications() {
  /**
   * Show an error toast notification
   * @param {string} message - Error message to display
   * @param {number} duration - Duration in milliseconds (default: 5000)
   */
  function showError(message, duration = 5000) {
    errorToastMessage.value = message;
    showErrorToast.value = true;

    setTimeout(() => {
      errorToastVisible.value = true;
    }, 10);

    if (errorToastTimer) {
      clearTimeout(errorToastTimer);
    }
    errorToastTimer = setTimeout(hideError, duration);
  }

  /**
   * Hide error toast notification
   */
  function hideError() {
    errorToastVisible.value = false;
    setTimeout(() => {
      showErrorToast.value = false;
    }, 300);

    if (errorToastTimer) {
      clearTimeout(errorToastTimer);
      errorToastTimer = null;
    }
  }

  /**
   * Show a success toast notification
   * @param {string} message - Success message to display
   * @param {number} duration - Duration in milliseconds (default: 3000)
   */
  function showSuccess(message, duration = 3000) {
    successToastMessage.value = message;
    showSuccessToast.value = true;

    setTimeout(() => {
      successToastVisible.value = true;
    }, 10);

    if (successToastTimer) {
      clearTimeout(successToastTimer);
    }
    successToastTimer = setTimeout(hideSuccess, duration);
  }

  /**
   * Hide success toast notification
   */
  function hideSuccess() {
    successToastVisible.value = false;
    setTimeout(() => {
      showSuccessToast.value = false;
    }, 300);

    if (successToastTimer) {
      clearTimeout(successToastTimer);
      successToastTimer = null;
    }
  }

  /**
   * Clear all active notifications
   */
  function clearAll() {
    hideError();
    hideSuccess();
  }

  /**
   * Cleanup timers (call in onUnmounted)
   */
  function cleanup() {
    if (errorToastTimer) {
      clearTimeout(errorToastTimer);
      errorToastTimer = null;
    }
    if (successToastTimer) {
      clearTimeout(successToastTimer);
      successToastTimer = null;
    }
  }

  return {
    // Error toast state (globally shared)
    showErrorToast,
    errorToastVisible,
    errorToastMessage,

    // Success toast state (globally shared)
    showSuccessToast,
    successToastVisible,
    successToastMessage,

    // Methods
    showError,
    hideError,
    showSuccess,
    hideSuccess,
    clearAll,
    cleanup,
  };
}
