/**
 * Password validation utilities
 */

/**
 * Calculate password strength score
 * @param {string} password - Password to evaluate
 * @returns {number} Strength score from 0-5
 */
export function calculatePasswordStrength(password) {
  if (!password) return 0;

  let score = 0;
  if (password.length < 10) return 1;
  if (password.length >= 12) score += 1;
  if (password.length >= 16) score += 1;

  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  return Math.min(score, 5);
}

/**
 * Get password strength text description
 * @param {number} strength - Strength score from calculatePasswordStrength
 * @returns {string} Text description
 */
export function getPasswordStrengthText(strength) {
  if (strength <= 1) return "Weak";
  if (strength <= 2) return "Fair";
  if (strength <= 3) return "Good";
  if (strength <= 4) return "Strong";
  return "Very Strong";
}

/**
 * Get password strength color classes
 * @param {number} strength - Strength score from calculatePasswordStrength
 * @returns {string} CSS color classes
 */
export function getPasswordStrengthColor(strength) {
  if (strength <= 1) return "text-red-600 bg-red-600";
  if (strength <= 2) return "text-orange-600 bg-orange-600";
  if (strength <= 3) return "text-yellow-600 bg-yellow-600";
  if (strength <= 4) return "text-blue-600 bg-blue-600";
  return "text-green-600 bg-green-600";
}

/**
 * Get password strength percentage for progress bar
 * @param {number} strength - Strength score from calculatePasswordStrength
 * @returns {number} Percentage (0-100)
 */
export function getPasswordStrengthPercentage(strength) {
  return (strength / 5) * 100;
}

/**
 * Validate password with comprehensive rules
 * @param {string} password - Password to validate
 * @returns {Object} Validation result with isValid and errors array
 */
export function validatePassword(password) {
  const errors = [];

  if (!password) {
    errors.push("Please enter a password");
  } else if (password.length < 10) {
    errors.push("Password must be at least 10 characters");
  } else if (password.length > 32) {
    errors.push("Password cannot exceed 32 characters");
  } else if (!/(?=.*[a-zA-Z])(?=.*[0-9])/.test(password)) {
    errors.push("Password must contain both letters and numbers");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Validate password confirmation
 * @param {string} password - Original password
 * @param {string} confirmPassword - Confirmation password
 * @returns {Object} Validation result with isValid and errors array
 */
export function validatePasswordConfirmation(password, confirmPassword) {
  const errors = [];

  if (!confirmPassword) {
    errors.push("Please confirm your password");
  } else if (password !== confirmPassword) {
    errors.push("Passwords do not match");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}
