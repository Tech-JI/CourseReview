// Lightweight API utilities used across components
// checkAuthentication: returns a boolean indicating auth status
export async function checkAuthentication() {
  try {
    const response = await fetch("/api/user/status/");
    if (response.ok) {
      const data = await response.json();
      return !!data.isAuthenticated;
    }
    return false;
  } catch (e) {
    console.error("Error checking authentication:", e);
    return false;
  }
}

export default { checkAuthentication };
