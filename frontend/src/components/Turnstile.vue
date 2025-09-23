<template>
  <div class="turnstile-container">
    <!-- Error State -->
    <div v-if="error" class="rounded-lg bg-red-50 p-4 mb-4">
      <div class="flex">
        <div class="ml-3">
          <h3 class="text-sm/6 font-medium text-red-800">
            Security Verification Error
          </h3>
          <div class="mt-2 text-sm/6 text-red-700">
            <p>{{ error }}</p>
          </div>
          <div class="mt-4">
            <button
              type="button"
              class="rounded-md bg-red-50 px-2 py-1.5 text-sm/6 font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
              @click="resetTurnstile"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Turnstile Widget Wrapper - Always render this to ensure DOM container exists -->
    <div v-else class="turnstile-widget-wrapper">
      <!-- Loading State -->
      <div v-if="loading" class="text-center">
        <div
          class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"
        ></div>
        <p class="mt-2 text-sm/6 text-gray-500">
          Loading security verification...
        </p>
      </div>

      <!-- Success State -->
      <div v-else-if="token" class="rounded-lg bg-green-50 p-4">
        <div class="flex">
          <div class="ml-3">
            <h3 class="text-sm/6 font-medium text-green-800">
              Security Check Complete
            </h3>
            <div class="mt-2 text-sm/6 text-green-700">
              <p>Verification successful. You may proceed.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Widget Content -->
      <div v-else>
        <div v-if="showTitle" class="text-center mb-4">
          <h3 class="text-lg/7 font-medium text-gray-900 mb-2">
            Verify you're human
          </h3>
          <p class="text-sm/6 text-gray-500">
            Complete the security check below to continue
          </p>
        </div>
        <div class="flex justify-center">
          <div :id="containerId"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from "vue";

// Props
const props = defineProps({
  size: {
    type: String,
    default: "normal",
    validator: (value) => ["normal", "compact", "flexible"].includes(value),
  },
  theme: {
    type: String,
    default: "light",
    validator: (value) => ["light", "dark", "auto"].includes(value),
  },
  showTitle: {
    type: Boolean,
    default: true,
  },
});

// Emits
const emit = defineEmits(["token", "error", "expired", "ready"]);

// Reactive state
const loading = ref(true);
const error = ref(null);
const token = ref(null);
const siteKey = ref(import.meta.env.VITE_TURNSTILE_SITE_KEY);

// Allow a local/dev mock token when real Turnstile cannot be loaded.
// Enable by setting VITE_TURNSTILE_MOCK=true in your .env (only for local/dev).
const allowMock =
  import.meta.env.VITE_TURNSTILE_MOCK === "true" ||
  location.hostname === "localhost" ||
  location.hostname === "127.0.0.1";

const createMockToken = () => `dev-turnstile-token-${Date.now()}`;

const fallbackToMock = () => {
  if (!allowMock) return false;
  console.warn(
    "Turnstile: falling back to mock token for development/testing.",
  );
  const mock = createMockToken();
  token.value = mock;
  loading.value = false;
  error.value = null;
  emit("token", mock);
  emit("ready");
  return true;
};

// Widget management
let turnstileWidget = null;

// Generate unique container ID for this instance
const containerId = `turnstile-widget-${Math.random()
  .toString(36)
  .substr(2, 9)}`;

// Success callback
const onSuccess = (receivedToken) => {
  token.value = receivedToken;
  loading.value = false;
  emit("token", receivedToken);
  emit("ready");
};

// Error callback
const onError = (errorCode) => {
  console.error("Turnstile error:", errorCode);
  const errorMessage = "Security verification failed. Please try again.";
  error.value = errorMessage;
  loading.value = false;
  emit("error", errorMessage);
};

// Expired callback
const onExpired = () => {
  console.log("Turnstile expired");
  token.value = null;
  const errorMessage = "Security verification expired. Please try again.";
  error.value = errorMessage;
  emit("expired", errorMessage);
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
      existingScript.addEventListener("load", resolve);
      existingScript.addEventListener("error", reject);
      return;
    }

    const script = document.createElement("script");
    script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
    script.async = true;
    script.addEventListener("load", resolve);
    script.addEventListener("error", (ev) => {
      // If loading the script errors and we're allowed to mock, resolve so caller
      // will render the mock token state; otherwise reject to surface the error.
      if (allowMock) {
        console.warn(
          "Turnstile script failed to load; allowMock=true -> using mock token",
        );
        resolve();
      } else {
        reject(ev);
      }
    });
    document.head.appendChild(script);
  });
};

// Render the Turnstile widget
const renderWidget = async () => {
  // Set loading to false first to ensure DOM is rendered
  loading.value = false;

  // Wait for DOM to be ready
  await nextTick();
  await nextTick();
  await nextTick(); // Extra wait to ensure DOM is fully rendered

  // Try to find the container with retries
  let container = null;
  let attempts = 0;
  const maxAttempts = 10;

  while (!container && attempts < maxAttempts) {
    container = document.getElementById(containerId);
    if (!container) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      attempts++;
    }
  }

  if (!container) {
    console.error("Turnstile container not found after waiting:", containerId);
    error.value =
      "Failed to initialize security verification. Please try again.";
    return;
  }

  // Clear any existing content
  container.innerHTML = "";

  try {
    turnstileWidget = window.turnstile.render(container, {
      sitekey: siteKey.value,
      callback: onSuccess,
      "error-callback": onError,
      "expired-callback": onExpired,
      theme: props.theme,
      size: props.size,
    });
  } catch (err) {
    console.error("Failed to render Turnstile widget:", err);
    error.value =
      "Failed to initialize security verification. Please try again.";
  }
};

// Cleanup widget
const cleanupWidget = () => {
  if (turnstileWidget && window.turnstile) {
    try {
      window.turnstile.remove(turnstileWidget);
    } catch (e) {
      console.warn("Error removing turnstile widget:", e);
    }
  }
  turnstileWidget = null;

  // Clear the container
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = "";
  }
};

// Reset turnstile
const resetTurnstile = async () => {
  error.value = null;
  token.value = null;
  loading.value = true;

  cleanupWidget();

  // Re-render the widget
  if (window.turnstile) {
    await renderWidget();
  } else {
    // If script not loaded, reload it
    try {
      await loadTurnstile();
      await renderWidget();
    } catch (err) {
      console.error("Failed to reload Turnstile:", err);
      error.value = "Failed to reload security verification. Please try again.";
      loading.value = false;
    }
  }
};

// Expose methods for parent components
defineExpose({
  resetTurnstile,
  getToken: () => token.value,
  isReady: () => !!token.value && !error.value && !loading.value,
});

// Component lifecycle
onMounted(async () => {
  try {
    await loadTurnstile();
    await renderWidget();
  } catch (err) {
    console.error("Failed to load Turnstile:", err);
    // If mocking is allowed, try to fallback to a mock token so local dev isn't blocked
    const usedMock = fallbackToMock();
    if (usedMock) {
      return;
    }

    const errorMessage =
      "Failed to load security verification. Please try again (network error).";
    error.value = errorMessage;
    loading.value = false;
    emit("error", errorMessage);
  }
});

onUnmounted(() => {
  cleanupWidget();
});
</script>

<style scoped>
.turnstile-container {
  max-width: 100%;
}

.turnstile-widget-wrapper {
  padding: 1rem;
}
</style>
