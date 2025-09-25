/**
 * Authentication utilities - centralized auth state management
 */

/**
 * Get authentication state from various storage sources
 * @returns {Object|null} Auth state object or null if not found
 */
export function getAuthState() {
  try {
    // Check URL parameters first (highest priority)
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

    // Check for simple verified state in URL
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

    // Check localStorage
    const localStorageState = localStorage.getItem("auth_flow");
    if (localStorageState) {
      const parsed = JSON.parse(localStorageState);
      return { ...parsed, source: "localStorage" };
    }

    // Check sessionStorage
    const sessionStorageState = sessionStorage.getItem("auth_flow");
    if (sessionStorageState) {
      const parsed = JSON.parse(sessionStorageState);
      return { ...parsed, source: "sessionStorage" };
    }

    // Check backup sessionStorage location
    const backupSessionState = sessionStorage.getItem("auth_verification_data");
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

/**
 * Clear all authentication state from storage
 */
export function clearAuthState() {
  try {
    localStorage.removeItem("auth_flow");
    localStorage.removeItem("auth_otp");
    localStorage.removeItem("auth_redirect_time");
    localStorage.removeItem("authState");
    sessionStorage.removeItem("auth_flow");
    sessionStorage.removeItem("auth_verification_data");
  } catch (error) {
    console.error("Failed to clear auth state:", error);
  }
}

/**
 * Save authentication state to storage
 * @param {Object} state - Auth state to save
 * @param {boolean} persistent - Whether to save to localStorage (true) or sessionStorage (false)
 */
export function saveAuthState(state, persistent = true) {
  try {
    const stateToSave = { ...state };
    delete stateToSave.source; // Remove source field before saving

    const stateString = JSON.stringify(stateToSave);

    if (persistent) {
      localStorage.setItem("auth_flow", stateString);
    }
    sessionStorage.setItem("auth_flow", stateString);
  } catch (error) {
    console.error("Failed to save auth state:", error);
  }
}

/**
 * Check if current auth state is valid for given action
 * @param {string} action - The action to validate against
 * @returns {boolean} Whether the current state is valid
 */
export function isAuthStateValid(action) {
  const state = getAuthState();
  return (
    state &&
    state.action === action &&
    state.status === "verified" &&
    (!state.expires_at || Date.now() < parseInt(state.expires_at))
  );
}
