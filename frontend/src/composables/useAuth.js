import { ref, onMounted, onUnmounted } from "vue";
import { checkAuthentication as checkAuthUtil } from "../utils/api";
import { getCookie } from "../utils/cookies";

export function useAuth() {
  const isAuthenticated = ref(false);

  const checkAuthentication = async () => {
    try {
      const auth = await checkAuthUtil();
      isAuthenticated.value = !!auth;
      return isAuthenticated.value;
    } catch (e) {
      console.error("useAuth: checkAuthentication error:", e);
      isAuthenticated.value = false;
      return false;
    }
  };

  const logout = async () => {
    try {
      const response = await fetch("/api/auth/logout/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });
      if (response.ok) {
        isAuthenticated.value = false;
        return true;
      } else {
        console.error("useAuth: logout failed", response.status);
        return false;
      }
    } catch (e) {
      console.error("useAuth: logout error:", e);
      return false;
    }
  };

  const onAuthStateChanged = () => {
    // Re-check authentication when other parts of app signal change
    checkAuthentication();
  };

  onMounted(() => {
    checkAuthentication();
    window.addEventListener("auth-state-changed", onAuthStateChanged);
  });

  onUnmounted(() => {
    window.removeEventListener("auth-state-changed", onAuthStateChanged);
  });

  return {
    isAuthenticated,
    checkAuthentication,
    logout,
  };
}

export default { useAuth };
