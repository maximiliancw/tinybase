<script setup lang="ts">
/**
 * Schedules View
 *
 * Manage function schedules (admin only).
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, watch, computed, h } from "vue";
import { useToast } from "vue-toastification";
import { useRoute } from "vue-router";
import { useForm, Field } from "vee-validate";
import {
  useFunctionsStore,
  generateTemplateFromSchema,
} from "../stores/functions";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import FormField from "../components/FormField.vue";
import DataTable from "../components/DataTable.vue";

const toast = useToast();
const route = useRoute();
const functionsStore = useFunctionsStore();

const showCreateModal = ref(false);
const loadingSchema = ref(false);

const {
  handleSubmit,
  resetForm,
  watch: watchForm,
  setFieldValue,
} = useForm({
  validationSchema: validationSchemas.createSchedule,
  initialValues: {
    name: "",
    function_name: "",
    method: "interval" as "once" | "interval" | "cron",
    timezone: "UTC",
    unit: "hours",
    value: 1,
    cron: "0 * * * *",
    date: "",
    time: "",
    input_data: "{}",
  },
});

// Watch for function selection changes to fetch schema
watchForm(
  (values) => values.function_name,
  async (functionName) => {
    if (!functionName) {
      setFieldValue("input_data", "{}");
      return;
    }

    loadingSchema.value = true;
    try {
      const schema = await functionsStore.fetchFunctionSchema(functionName);
      if (schema?.input_schema) {
        const template = generateTemplateFromSchema(schema.input_schema);
        setFieldValue("input_data", JSON.stringify(template, null, 2));
      } else {
        setFieldValue("input_data", "{}");
      }
    } catch {
      setFieldValue("input_data", "{}");
    } finally {
      loadingSchema.value = false;
    }
  }
);

onMounted(async () => {
  await functionsStore.fetchSchedules();
  await functionsStore.fetchFunctions();
  if (route.query.action === "create") {
    showCreateModal.value = true;
  }
});

function buildSchedulePayload(values: any) {
  const base = {
    timezone: values.timezone,
  };

  switch (values.method) {
    case "interval":
      return {
        ...base,
        method: "interval",
        unit: values.unit,
        value: values.value,
      };
    case "cron":
      return {
        ...base,
        method: "cron",
        cron: values.cron,
      };
    case "once":
      return {
        ...base,
        method: "once",
        date: values.date,
        time: values.time,
      };
  }
}

const onSubmit = handleSubmit(async (values) => {
  let inputData = {};
  try {
    inputData = JSON.parse(values.input_data);
  } catch {
    toast.error("Invalid JSON in input data");
    return;
  }

  const result = await functionsStore.createSchedule({
    name: values.name,
    function_name: values.function_name,
    schedule: buildSchedulePayload(values),
    input_data: inputData,
  });

  if (result) {
    toast.success(`Schedule "${values.name}" created successfully`);
    showCreateModal.value = false;
    resetForm({
      values: {
        name: "",
        function_name: "",
        method: "interval",
        timezone: "UTC",
        unit: "hours",
        value: 1,
        cron: "0 * * * *",
        date: "",
        time: "",
        input_data: "{}",
      },
    });
  } else {
    toast.error(functionsStore.error || "Failed to create schedule");
  }
});

async function handleToggleActive(scheduleId: string, currentStatus: boolean) {
  const result = await functionsStore.updateSchedule(scheduleId, {
    is_active: !currentStatus,
  });
  if (result) {
    toast.success(`Schedule ${!currentStatus ? "activated" : "paused"}`);
  } else {
    toast.error(functionsStore.error || "Failed to update schedule");
  }
}

async function handleDelete(scheduleId: string) {
  if (confirm("Are you sure you want to delete this schedule?")) {
    const result = await functionsStore.deleteSchedule(scheduleId);
    if (result) {
      toast.success("Schedule deleted successfully");
    } else {
      toast.error(functionsStore.error || "Failed to delete schedule");
    }
  }
}

function formatSchedule(schedule: any): string {
  switch (schedule.method) {
    case "interval":
      return `Every ${schedule.value} ${schedule.unit}`;
    case "cron":
      return `Cron: ${schedule.cron}`;
    case "once":
      return `Once: ${schedule.date} ${schedule.time}`;
    default:
      return "Unknown";
  }
}

const scheduleColumns = computed(() => [
  { key: "name", label: "Name" },
  {
    key: "function_name",
    label: "Function",
    render: (value: any) => h("code", value),
  },
  {
    key: "schedule",
    label: "Schedule",
    render: (_value: any, row: any) =>
      h("small", { class: "text-muted" }, formatSchedule(row.schedule)),
  },
  {
    key: "status",
    label: "Status",
    render: (_value: any, row: any) =>
      h(
        "mark",
        { "data-status": row.is_active ? "success" : "neutral" },
        row.is_active ? "Active" : "Inactive"
      ),
  },
  {
    key: "next_run_at",
    label: "Next Run",
    render: (value: any) =>
      h(
        "small",
        { class: "text-muted" },
        value ? new Date(value).toLocaleString() : "-"
      ),
  },
  {
    key: "actions",
    label: "Actions",
    actions: [
      {
        label: (row: any) => (row.is_active ? "Pause" : "Resume"),
        action: (row: any) => handleToggleActive(row.id, row.is_active),
        variant: "secondary" as const,
      },
      {
        label: "Delete",
        action: (row: any) => handleDelete(row.id),
        variant: "contrast" as const,
      },
    ],
  },
]);
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>Schedules</h1>
        <p>Manage function schedules</p>
      </hgroup>
      <button @click="showCreateModal = true">+ New Schedule</button>
    </header>

    <!-- Loading State -->
    <article v-if="functionsStore.loading" aria-busy="true">
      Loading schedules...
    </article>

    <!-- Empty State -->
    <article v-else-if="functionsStore.schedules.length === 0">
      <div data-empty data-empty-icon="⏰">
        <p>No schedules yet</p>
        <p>
          <small class="text-muted"
            >Create schedules to run functions automatically.</small
          >
        </p>
        <button class="small mt-2" @click="showCreateModal = true">
          Create Schedule
        </button>
      </div>
    </article>

    <!-- Schedules Table -->
    <article v-else>
      <DataTable
        :data="functionsStore.schedules"
        :columns="scheduleColumns"
        :page-size="20"
        search-placeholder="Search schedules..."
      />
    </article>

    <!-- Create Schedule Modal -->
    <Modal v-model:open="showCreateModal" title="Create Schedule">
      <form id="schedule-form" @submit="onSubmit">
        <FormField name="name" type="text" label="Name" />

        <FormField name="function_name" as="select" label="Function">
          <option value="">Select a function</option>
          <option
            v-for="fn in functionsStore.functions"
            :key="fn.name"
            :value="fn.name"
          >
            {{ fn.name }}
          </option>
        </FormField>

        <Field name="method" v-slot="{ field }">
          <fieldset>
            <legend>Schedule Type</legend>
            <label>
              <input type="radio" v-bind="field" value="interval" />
              Interval
            </label>
            <label>
              <input type="radio" v-bind="field" value="cron" />
              Cron
            </label>
            <label>
              <input type="radio" v-bind="field" value="once" />
              Once
            </label>
          </fieldset>
        </Field>

        <Field name="method" v-slot="{ value: method }">
          <!-- Interval Options -->
          <div v-if="method === 'interval'" class="grid">
            <FormField name="value" type="number" label="Value" :min="1" />
            <FormField name="unit" as="select" label="Unit">
              <option value="seconds">Seconds</option>
              <option value="minutes">Minutes</option>
              <option value="hours">Hours</option>
              <option value="days">Days</option>
            </FormField>
          </div>

          <!-- Cron Options -->
          <FormField
            v-if="method === 'cron'"
            name="cron"
            type="text"
            label="Cron Expression"
            placeholder="0 * * * *"
            helper="Format: minute hour day_of_month month day_of_week"
          />

          <!-- Once Options -->
          <div v-if="method === 'once'" class="grid">
            <FormField name="date" type="date" label="Date" />
            <FormField name="time" type="time" label="Time" />
          </div>
        </Field>

        <FormField
          name="timezone"
          type="text"
          label="Timezone"
          placeholder="UTC"
        />

        <!-- Input Data -->
        <Field name="input_data" v-slot="{ field, errors, meta }">
          <label for="field-input_data">
            Input Data (JSON)
            <textarea
              v-if="loadingSchema"
              id="field-input_data"
              rows="6"
              disabled
              aria-busy="true"
              class="code-editor"
            >
Loading schema...</textarea
            >
            <textarea
              v-else
              id="field-input_data"
              v-bind="field"
              rows="6"
              class="code-editor"
              spellcheck="false"
              placeholder="{}"
              :aria-invalid="meta.touched && !meta.valid ? 'true' : 'false'"
            ></textarea>
            <small v-if="meta.touched && errors[0]" class="text-error">
              {{ errors[0] }}
            </small>
            <small v-else>Data to pass to the function when executed</small>
          </label>
        </Field>
      </form>
      <template #footer>
        <button
          type="button"
          class="secondary"
          @click="showCreateModal = false"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="schedule-form"
          :aria-busy="functionsStore.loading"
          :disabled="functionsStore.loading"
        >
          {{ functionsStore.loading ? "" : "Create Schedule" }}
        </button>
      </template>
    </Modal>
  </section>
</template>

<style scoped>
/* Page header layout */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header hgroup {
  margin: 0;
}

.page-header hgroup h1 {
  margin-bottom: var(--tb-spacing-xs);
}

.page-header hgroup p {
  margin: 0;
  color: var(--pico-muted-color);
}

/* Code editor textarea */
.code-editor {
  font-family: ui-monospace, "SF Mono", "Cascadia Code", "Source Code Pro",
    Menlo, Consolas, monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  tab-size: 2;
  resize: vertical;
}
</style>
