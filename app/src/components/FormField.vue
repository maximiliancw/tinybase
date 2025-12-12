<script setup lang="ts">
/**
 * FormField Component
 *
 * Reusable form field component that integrates VeeValidate with PicoCSS validation states.
 * Handles label, input, error message display, and applies proper ARIA attributes.
 *
 * Usage:
 *   <FormField name="email" type="email" label="Email" />
 *   <FormField name="password" type="password" label="Password" />
 *   <FormField name="role" as="select" label="Role">
 *     <option value="">Select...</option>
 *     <option value="admin">Admin</option>
 *   </FormField>
 */
import { computed } from "vue";
import { Field } from "vee-validate";

interface Props {
  /** Field name for VeeValidate */
  name: string;
  /** Input type (text, email, password, etc.) */
  type?: string;
  /** Label text */
  label?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Helper text shown below input */
  helper?: string;
  /** Whether field is required */
  required?: boolean;
  /** Whether field is disabled */
  disabled?: boolean;
  /** Whether field is readonly */
  readonly?: boolean;
  /** Render as different element (select, textarea) */
  as?: "input" | "select" | "textarea";
  /** Rows for textarea */
  rows?: number;
}

const props = withDefaults(defineProps<Props>(), {
  type: "text",
  label: undefined,
  placeholder: undefined,
  helper: undefined,
  required: false,
  disabled: false,
  readonly: false,
  as: "input",
});

// Generate unique ID for aria-describedby
const fieldId = computed(() => `field-${props.name}`);
const helperId = computed(() => `${fieldId.value}-helper`);
const errorId = computed(() => `${fieldId.value}-error`);

// Determine which ID to use for aria-describedby
const describedBy = computed(() => {
  const ids: string[] = [];
  if (props.helper) ids.push(helperId.value);
  return ids.join(" ");
});
</script>

<template>
  <Field
    :name="name"
    v-slot="{ field, meta, errors }"
  >
    <label :for="fieldId">
      <span v-if="label">{{ label }}</span>
      <component
        :is="as"
        :id="fieldId"
        v-bind="{ ...field, ...$attrs }"
        :type="as === 'input' ? type : undefined"
        :placeholder="placeholder"
        :required="required"
        :disabled="disabled"
        :readonly="readonly"
        :rows="as === 'textarea' ? rows : undefined"
        :aria-invalid="meta.touched && !meta.valid ? 'true' : meta.touched && meta.valid ? 'false' : undefined"
        :aria-describedby="
          (meta.touched && errors[0] ? errorId + ' ' : '') + describedBy
        "
      >
        <slot />
      </component>
      <small v-if="helper && !(meta.touched && errors[0])" :id="helperId">
        {{ helper }}
      </small>
      <small
        v-if="meta.touched && errors[0]"
        :id="errorId"
        class="text-error"
      >
        {{ errors[0] }}
      </small>
    </label>
  </Field>
</template>

<style scoped>
/* Error messages inherit validation state color from PicoCSS */
.text-error {
  color: var(--pico-form-element-invalid-border-color, var(--pico-del-color));
}
</style>

