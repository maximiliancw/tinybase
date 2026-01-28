/**
 * Form Dialog Composable
 *
 * Combines modal state management with form handling using VeeValidate.
 * Reduces boilerplate for the common pattern of dialog forms.
 */
import { useModal, type UseModalOptions } from './useModal';
import { useForm, useField } from 'vee-validate';
import { useToast } from './useToast';
import type { AnySchema } from 'yup';

export interface UseFormDialogOptions<T extends Record<string, unknown>> extends UseModalOptions {
  /**
   * Yup validation schema for the form.
   */
  validationSchema: AnySchema;

  /**
   * Initial form values.
   */
  initialValues: T;

  /**
   * Callback when form is submitted successfully.
   * Should return true if the operation succeeded, false otherwise.
   */
  onSubmit: (values: T) => Promise<boolean>;

  /**
   * Success message to show after successful submission.
   * Can be a string or a function that receives the submitted values.
   */
  successMessage: string | ((values: T) => string);

  /**
   * Error message to show when submission fails.
   */
  errorMessage: string;

  /**
   * Whether to reset the form after successful submission.
   * @default true
   */
  resetOnSuccess?: boolean;

  /**
   * Whether to close the dialog after successful submission.
   * @default true
   */
  closeOnSuccess?: boolean;
}

/**
 * Composable that combines modal state with form handling.
 *
 * @example
 * const { isOpen, open, close, submit, fields } = useFormDialog({
 *   validationSchema: validationSchemas.createUser,
 *   initialValues: { email: '', password: '', is_admin: false },
 *   onSubmit: async (values) => {
 *     return await store.createUser(values);
 *   },
 *   successMessage: (values) => `User "${values.email}" created successfully`,
 *   errorMessage: 'Failed to create user',
 * });
 */
export function useFormDialog<T extends Record<string, unknown>>(
  options: UseFormDialogOptions<T>
) {
  const {
    validationSchema,
    initialValues,
    onSubmit,
    successMessage,
    errorMessage,
    resetOnSuccess = true,
    closeOnSuccess = true,
    ...modalOptions
  } = options;

  const { isOpen, open, close, toggle } = useModal(modalOptions);
  const toast = useToast();

  const { handleSubmit, resetForm, errors, values, meta, setFieldValue, setValues } = useForm<T>({
    validationSchema,
    initialValues,
  });

  /**
   * Submit handler that wraps the provided onSubmit callback.
   * Handles success/error toasts and form reset.
   */
  const submit = handleSubmit(async (formValues) => {
    const result = await onSubmit(formValues as T);

    if (result) {
      const message =
        typeof successMessage === 'function'
          ? successMessage(formValues as T)
          : successMessage;
      toast.success(message);

      if (closeOnSuccess) {
        close();
      }

      if (resetOnSuccess) {
        resetForm();
      }
    } else {
      toast.error(errorMessage);
    }
  });

  /**
   * Open the modal and optionally reset the form to initial values.
   */
  const openWithReset = () => {
    resetForm();
    open();
  };

  /**
   * Open the modal with specific values (for edit mode).
   */
  const openWithValues = (newValues: Partial<T>) => {
    setValues({ ...initialValues, ...newValues });
    open();
  };

  return {
    // Modal state
    isOpen,
    open,
    close,
    toggle,
    openWithReset,
    openWithValues,

    // Form state
    submit,
    resetForm,
    errors,
    values,
    meta,
    setFieldValue,
    setValues,

    // Re-export useField for convenience
    useField,
  };
}
