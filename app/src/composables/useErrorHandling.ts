/**
 * Error Handling Composable
 *
 * Provides utilities for handling API errors with different behavior
 * in development vs production environments.
 */

/**
 * Formats an error message based on the environment and error type.
 *
 * @param error - The error object from axios or a catch block
 * @param defaultMessage - Default message to show if error details aren't available
 * @returns Formatted error message appropriate for the environment
 */
export function formatErrorMessage(
  error: any,
  defaultMessage: string = "An error occurred"
): string {
  const isDevelopment =
    import.meta.env.DEV || import.meta.env.MODE === "development";

  // Try to get error details from response
  const statusCode = error.response?.status;
  const errorDetail = error.response?.data?.detail;
  const errorMessage = error.message;

  // In development, show full error details
  if (isDevelopment) {
    if (errorDetail) {
      return errorDetail;
    }
    if (errorMessage && errorMessage !== "Network Error") {
      return errorMessage;
    }
    if (statusCode) {
      return `${defaultMessage} (Status: ${statusCode})`;
    }
    return errorMessage || defaultMessage;
  }

  // In production, show user-friendly messages
  if (statusCode) {
    // 5XX errors - server errors
    if (statusCode >= 500) {
      return "Something went wrong on our end. Please try again soon or contact our support team if the problem persists.";
    }
    // 4XX errors - client errors, show detail if available
    if (statusCode >= 400 && statusCode < 500) {
      return errorDetail || defaultMessage;
    }
  }

  // Network errors or other issues
  if (errorMessage === "Network Error" || !error.response) {
    return "Unable to connect to the server. Please check your internet connection and try again.";
  }

  return errorDetail || defaultMessage;
}
