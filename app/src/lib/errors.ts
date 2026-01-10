/**
 * Standardized error messages.
 *
 * Use these constants for consistent error messaging across the application.
 */
export const ErrorMessages = {
  /**
   * Resource not found error message.
   *
   * @param resource - Name of the resource (e.g., 'User', 'Match')
   * @returns Formatted error message
   */
  NOT_FOUND: (resource: string) => `${resource} not found`,

  /**
   * Authentication required error message.
   */
  UNAUTHORIZED: 'Authentication required',

  /**
   * Access denied error message.
   */
  FORBIDDEN: 'Access denied',

  /**
   * Invalid input error message.
   */
  VALIDATION_ERROR: 'Invalid input',

  /**
   * Subscription required error message.
   */
  SUBSCRIPTION_REQUIRED: 'Subscription required',
} as const;
