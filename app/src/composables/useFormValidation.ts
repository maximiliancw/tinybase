/**
 * Form Validation Utilities
 *
 * Common validation rules and schemas for use with VeeValidate and Yup.
 * Provides reusable validation patterns across the application.
 */
import * as yup from 'yup';

/**
 * Common validation rules as Yup schemas
 */
export const validationRules = {
  /**
   * Email validation
   */
  email: () =>
    yup.string().email('Please enter a valid email address').required('Email is required'),

  /**
   * Required string
   */
  required: (message = 'This field is required') => yup.string().required(message),

  /**
   * Password validation
   */
  password: (minLength = 8) =>
    yup
      .string()
      .min(minLength, `Password must be at least ${minLength} characters`)
      .required('Password is required'),

  /**
   * URL validation (for GitHub URLs, extension installation, etc.)
   */
  url: (message = 'Please enter a valid URL') =>
    yup.string().url(message).required('URL is required'),

  /**
   * GitHub URL validation
   */
  githubUrl: () =>
    yup
      .string()
      .url('Please enter a valid URL')
      .matches(
        /^https:\/\/github\.com\/[\w\-\.]+\/[\w\-\.]+/,
        'Please enter a valid GitHub repository URL (e.g., https://github.com/username/repo)'
      )
      .required('GitHub URL is required'),

  /**
   * Snake case validation (for collection names, etc.)
   */
  snakeCase: (
    message = 'Must be in snake_case format (lowercase letters, numbers, and underscores)'
  ) =>
    yup
      .string()
      .matches(/^[a-z][a-z0-9_]*$/, message)
      .required('This field is required'),

  /**
   * JSON validation
   */
  json: (message = 'Please enter valid JSON') =>
    yup.string().test('is-json', message, (value) => {
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
  positiveNumber: (message = 'Must be a positive number') =>
    yup.number().positive(message).required('This field is required'),

  /**
   * Non-empty string
   */
  nonEmpty: (message = 'This field cannot be empty') =>
    yup.string().min(1, message).required('This field is required'),
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
    password: yup.string().required('Password is required'),
  }),

  /**
   * Change password schema
   */
  changePassword: yup.object({
    currentPassword: yup.string().required('Current password is required'),
    newPassword: validationRules.password(8),
    confirmPassword: yup
      .string()
      .required('Please confirm your new password')
      .test('passwords-match', 'Passwords must match', function (value) {
        return value === this.parent.newPassword;
      }),
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
    label: validationRules.nonEmpty('Label is required'),
    schemaText: validationRules.json('Please enter valid JSON schema'),
  }),

  /**
   * File upload schema
   */
  uploadFile: yup.object({
    file: yup
      .mixed<File>()
      .required('Please select a file')
      .test('file-exists', 'Please select a file', (value) => {
        return value instanceof File;
      }),
    path_prefix: yup.string().optional(),
  }),

  /**
   * Schedule creation schema (with conditional validation)
   */
  createSchedule: yup.object({
    name: validationRules.nonEmpty('Schedule name is required'),
    function_name: validationRules.nonEmpty('Please select a function'),
    method: yup
      .string()
      .oneOf(['once', 'interval', 'cron'], 'Invalid schedule method')
      .required('Schedule method is required'),
    timezone: yup.string().default('UTC'),
    // Interval fields
    unit: yup.string().when('method', {
      is: 'interval',
      then: (schema) => schema.required('Unit is required for interval schedules'),
      otherwise: (schema) => schema.optional(),
    }),
    value: yup.number().when('method', {
      is: 'interval',
      then: (schema) =>
        schema
          .positive('Value must be positive')
          .required('Value is required for interval schedules'),
      otherwise: (schema) => schema.optional(),
    }),
    // Cron fields
    cron: yup.string().when('method', {
      is: 'cron',
      then: (schema) => schema.required('Cron expression is required'),
      otherwise: (schema) => schema.optional(),
    }),
    // Once fields
    date: yup.string().when('method', {
      is: 'once',
      then: (schema) => schema.required('Date is required for one-time schedules'),
      otherwise: (schema) => schema.optional(),
    }),
    time: yup.string().when('method', {
      is: 'once',
      then: (schema) => schema.required('Time is required for one-time schedules'),
      otherwise: (schema) => schema.optional(),
    }),
    // Input data
    input_data: validationRules.json('Please enter valid JSON'),
  }),

  /**
   * Application token creation schema
   */
  createToken: yup.object({
    name: validationRules.nonEmpty('Token name is required'),
    description: yup.string().max(500, 'Description must be 500 characters or less').optional(),
    expires_days: yup
      .number()
      .positive('Expiration days must be positive')
      .min(1, 'Expiration days must be at least 1')
      .nullable()
      .optional(),
  }),

  /**
   * Settings form schema with conditional validation for auth portal
   */
  settings: yup.object({
    instance_name: yup
      .string()
      .max(100, 'Instance name must be 100 characters or less')
      .required('Instance name is required'),
    allow_public_registration: yup.boolean().required(),
    server_timezone: yup
      .string()
      .max(50, 'Timezone must be 50 characters or less')
      .required('Server timezone is required'),
    token_cleanup_interval: yup
      .number()
      .min(1, 'Token cleanup interval must be at least 1')
      .required('Token cleanup interval is required'),
    metrics_collection_interval: yup
      .number()
      .min(1, 'Metrics collection interval must be at least 1')
      .required('Metrics collection interval is required'),
    scheduler_function_timeout_seconds: yup
      .number()
      .min(1, 'Timeout must be at least 1 second')
      .nullable()
      .optional(),
    scheduler_max_schedules_per_tick: yup
      .number()
      .min(1, 'Max schedules per tick must be at least 1')
      .nullable()
      .optional(),
    scheduler_max_concurrent_executions: yup
      .number()
      .min(1, 'Max concurrent executions must be at least 1')
      .nullable()
      .optional(),
    storage_enabled: yup.boolean().required(),
    storage_endpoint: yup
      .string()
      .max(500, 'Endpoint must be 500 characters or less')
      .url('Please enter a valid URL')
      .nullable()
      .optional(),
    storage_bucket: yup
      .string()
      .max(100, 'Bucket name must be 100 characters or less')
      .nullable()
      .optional(),
    storage_region: yup
      .string()
      .max(50, 'Region must be 50 characters or less')
      .nullable()
      .optional(),
    auth_portal_enabled: yup.boolean().required(),
    auth_portal_logo_url: yup
      .string()
      .max(500, 'Logo URL must be 500 characters or less')
      .url('Please enter a valid URL')
      .nullable()
      .optional(),
    auth_portal_primary_color: yup
      .string()
      .max(50, 'Primary color must be 50 characters or less')
      .nullable()
      .optional(),
    auth_portal_background_image_url: yup
      .string()
      .max(500, 'Background image URL must be 500 characters or less')
      .url('Please enter a valid URL')
      .nullable()
      .optional(),
    // Conditional validation: required only if auth_portal_enabled is true
    auth_portal_login_redirect_url: yup
      .string()
      .max(500, 'Login redirect URL must be 500 characters or less')
      .when('auth_portal_enabled', {
        is: true,
        then: (schema) =>
          schema
            .required('Login redirect URL is required when auth portal is enabled')
            .url('Please enter a valid absolute URL (e.g., https://app.example.com/dashboard)')
            .test(
              'absolute-url',
              'Login redirect URL must be an absolute URL (start with http:// or https://)',
              (value) => {
                if (!value) return false;
                return value.startsWith('http://') || value.startsWith('https://');
              }
            )
            .test('no-admin', 'Login redirect URL must not point to /admin URLs', (value) => {
              if (!value) return false;
              return !value.includes('/admin');
            }),
        otherwise: (schema) => schema.nullable().optional(),
      }),
    auth_portal_register_redirect_url: yup
      .string()
      .max(500, 'Register redirect URL must be 500 characters or less')
      .when('auth_portal_enabled', {
        is: true,
        then: (schema) =>
          schema
            .required('Register redirect URL is required when auth portal is enabled')
            .url('Please enter a valid absolute URL (e.g., https://app.example.com/welcome)')
            .test(
              'absolute-url',
              'Register redirect URL must be an absolute URL (start with http:// or https://)',
              (value) => {
                if (!value) return false;
                return value.startsWith('http://') || value.startsWith('https://');
              }
            )
            .test('no-admin', 'Register redirect URL must not point to /admin URLs', (value) => {
              if (!value) return false;
              return !value.includes('/admin');
            }),
        otherwise: (schema) => schema.nullable().optional(),
      }),
  }),
};

/**
 * Helper function to create custom validation schemas
 */
export function createSchema(fields: Record<string, yup.AnySchema>) {
  return yup.object(fields);
}
