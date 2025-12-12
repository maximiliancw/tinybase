/**
 * Form Validation Utilities
 *
 * Common validation rules and schemas for use with VeeValidate and Yup.
 * Provides reusable validation patterns across the application.
 */
import * as yup from "yup";

/**
 * Common validation rules as Yup schemas
 */
export const validationRules = {
  /**
   * Email validation
   */
  email: () => yup.string().email("Please enter a valid email address").required("Email is required"),

  /**
   * Required string
   */
  required: (message = "This field is required") =>
    yup.string().required(message),

  /**
   * Password validation
   */
  password: (minLength = 8) =>
    yup
      .string()
      .min(minLength, `Password must be at least ${minLength} characters`)
      .required("Password is required"),

  /**
   * URL validation (for GitHub URLs, extension installation, etc.)
   */
  url: (message = "Please enter a valid URL") =>
    yup.string().url(message).required("URL is required"),

  /**
   * GitHub URL validation
   */
  githubUrl: () =>
    yup
      .string()
      .url("Please enter a valid URL")
      .matches(
        /^https:\/\/github\.com\/[\w\-\.]+\/[\w\-\.]+/,
        "Please enter a valid GitHub repository URL (e.g., https://github.com/username/repo)"
      )
      .required("GitHub URL is required"),

  /**
   * Snake case validation (for collection names, etc.)
   */
  snakeCase: (message = "Must be in snake_case format (lowercase letters, numbers, and underscores)") =>
    yup
      .string()
      .matches(/^[a-z][a-z0-9_]*$/, message)
      .required("This field is required"),

  /**
   * JSON validation
   */
  json: (message = "Please enter valid JSON") =>
    yup
      .string()
      .test("is-json", message, (value) => {
        if (!value) return true; // Allow empty if not required
        try {
          JSON.parse(value);
          return true;
        } catch {
          return false;
        }
      }),

  /**
   * Positive number
   */
  positiveNumber: (message = "Must be a positive number") =>
    yup.number().positive(message).required("This field is required"),

  /**
   * Non-empty string
   */
  nonEmpty: (message = "This field cannot be empty") =>
    yup.string().min(1, message).required("This field is required"),
};

/**
 * Common validation schemas
 */
export const validationSchemas = {
  /**
   * User creation schema
   */
  createUser: yup.object({
    email: validationRules.email(),
    password: validationRules.password(8),
    is_admin: yup.boolean().default(false),
  }),

  /**
   * Login schema
   */
  login: yup.object({
    email: validationRules.email(),
    password: yup.string().required("Password is required"),
  }),

  /**
   * Extension installation schema
   */
  installExtension: yup.object({
    repo_url: validationRules.githubUrl(),
  }),

  /**
   * Collection creation schema
   */
  createCollection: yup.object({
    name: validationRules.snakeCase(),
    label: validationRules.nonEmpty("Label is required"),
    schemaText: validationRules.json("Please enter valid JSON schema"),
  }),

  /**
   * File upload schema
   */
  uploadFile: yup.object({
    file: yup
      .mixed<File>()
      .required("Please select a file")
      .test("file-exists", "Please select a file", (value) => {
        return value instanceof File;
      }),
    path_prefix: yup.string().optional(),
  }),

  /**
   * Schedule creation schema (with conditional validation)
   */
  createSchedule: yup.object({
    name: validationRules.nonEmpty("Schedule name is required"),
    function_name: validationRules.nonEmpty("Please select a function"),
    method: yup
      .string()
      .oneOf(["once", "interval", "cron"], "Invalid schedule method")
      .required("Schedule method is required"),
    timezone: yup.string().default("UTC"),
    // Interval fields
    unit: yup.string().when("method", {
      is: "interval",
      then: (schema) => schema.required("Unit is required for interval schedules"),
      otherwise: (schema) => schema.optional(),
    }),
    value: yup.number().when("method", {
      is: "interval",
      then: (schema) =>
        schema
          .positive("Value must be positive")
          .required("Value is required for interval schedules"),
      otherwise: (schema) => schema.optional(),
    }),
    // Cron fields
    cron: yup.string().when("method", {
      is: "cron",
      then: (schema) => schema.required("Cron expression is required"),
      otherwise: (schema) => schema.optional(),
    }),
    // Once fields
    date: yup.string().when("method", {
      is: "once",
      then: (schema) => schema.required("Date is required for one-time schedules"),
      otherwise: (schema) => schema.optional(),
    }),
    time: yup.string().when("method", {
      is: "once",
      then: (schema) => schema.required("Time is required for one-time schedules"),
      otherwise: (schema) => schema.optional(),
    }),
    // Input data
    input_data: validationRules.json("Please enter valid JSON"),
  }),

  /**
   * Application token creation schema
   */
  createToken: yup.object({
    name: validationRules.nonEmpty("Token name is required"),
    description: yup.string().max(500, "Description must be 500 characters or less").optional(),
    expires_days: yup
      .number()
      .positive("Expiration days must be positive")
      .min(1, "Expiration days must be at least 1")
      .nullable()
      .optional(),
  }),
};

/**
 * Helper function to create custom validation schemas
 */
export function createSchema(fields: Record<string, yup.AnySchema>) {
  return yup.object(fields);
}

