<script setup lang="ts">
/**
 * Schedules View
 *
 * Manage function schedules (admin only).
 */
import { onMounted, ref, watch, computed, h } from "vue";
import { useToast } from "../composables/useToast";
import { useRoute } from "vue-router";
import { useUrlSearchParams } from "@vueuse/core";
import { useForm, Field, useField } from "vee-validate";
import {
  useFunctionsStore,
  generateTemplateFromSchema,
} from "../stores/functions";
import { validationSchemas } from "../composables/useFormValidation";
import DataTable from "../components/DataTable.vue";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const toast = useToast();
const route = useRoute();
const functionsStore = useFunctionsStore();

// URL search params for action=create
const params = useUrlSearchParams("history");
const action = computed(() => params.action as string | null);

const showCreateModal = ref(false);
const loadingSchema = ref(false);
const functionSchema = ref<any>(null);

const { handleSubmit, resetForm, values, setFieldValue } = useForm({
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

const nameField = useField("name");
const functionNameField = useField("function_name");
const methodField = useField("method");
const timezoneField = useField("timezone");
const unitField = useField("unit");
const valueField = useField("value");
const cronField = useField("cron");
const dateField = useField("date");
const timeField = useField("time");
const inputDataField = useField("input_data");

// Computed property to get selected function info
const selectedFunction = computed(() => {
  if (!values.function_name) return null;
  return (
    functionsStore.functions.find((f) => f.name === values.function_name) ||
    null
  );
});

// Function to fetch schema and generate template
async function fetchSchemaAndGenerateTemplate(functionName: string) {
  if (!functionName) {
    functionSchema.value = null;
    setFieldValue("input_data", "{}");
    return;
  }

  loadingSchema.value = true;
  try {
    const schema = await functionsStore.fetchFunctionSchema(functionName);
    functionSchema.value = schema;
    if (schema?.input_schema) {
      const template = generateTemplateFromSchema(schema.input_schema);
      setFieldValue("input_data", JSON.stringify(template, null, 2));
    } else {
      setFieldValue("input_data", "{}");
    }
  } catch {
    functionSchema.value = null;
    setFieldValue("input_data", "{}");
  } finally {
    loadingSchema.value = false;
  }
}

// Watch for function selection changes to fetch schema
watch(
  () => values.function_name,
  async (functionName) => {
    await fetchSchemaAndGenerateTemplate(functionName);
  },
  { immediate: false }
);

// Watch for modal opening/closing
watch(
  () => showCreateModal.value,
  async (isOpen) => {
    if (isOpen && values.function_name) {
      await fetchSchemaAndGenerateTemplate(values.function_name);
    } else if (!isOpen) {
      functionSchema.value = null;
    }
  }
);

// Watch for action=create in URL
watch(
  action,
  (newAction) => {
    if (newAction === "create") {
      showCreateModal.value = true;
      params.action = undefined;
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await functionsStore.fetchSchedules();
  await functionsStore.fetchFunctions();
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
    render: (value: any) => h("code", { class: "text-sm" }, value),
  },
  {
    key: "schedule",
    label: "Schedule",
    render: (_value: any, row: any) =>
      h("span", { class: "text-sm text-muted-foreground" }, formatSchedule(row.schedule)),
  },
  {
    key: "status",
    label: "Status",
    render: (_value: any, row: any) =>
      h(
        Badge,
        { variant: row.is_active ? "default" : "secondary" },
        () => (row.is_active ? "Active" : "Inactive")
      ),
  },
  {
    key: "next_run_at",
    label: "Next Run",
    render: (value: any) =>
      h(
        "span",
        { class: "text-sm text-muted-foreground" },
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
        variant: "destructive" as const,
      },
    ],
  },
]);
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Schedules</h1>
      <p class="text-muted-foreground">Manage function schedules</p>
    </header>

    <!-- Loading State -->
    <Card v-if="functionsStore.loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading schedules...</p>
      </CardContent>
    </Card>

    <!-- Empty State -->
    <Card v-else-if="functionsStore.schedules.length === 0">
      <CardContent class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted text-3xl">
          ⏰
        </div>
        <h3 class="mb-1 text-lg font-semibold">No schedules yet</h3>
        <p class="mb-4 text-sm text-muted-foreground">
          Create schedules to run functions automatically.
        </p>
        <Button size="sm" @click="showCreateModal = true">
          Create Schedule
        </Button>
      </CardContent>
    </Card>

    <!-- Schedules Table -->
    <Card v-else>
      <DataTable
        :data="functionsStore.schedules"
        :columns="scheduleColumns"
        :page-size="20"
        search-placeholder="Search schedules..."
        :header-action="{
          label: '+ New Schedule',
          action: () => {
            showCreateModal = true;
          },
          variant: 'default',
          icon: 'Plus',
        }"
      />
    </Card>

    <!-- Create Schedule Modal -->
    <Dialog v-model:open="showCreateModal">
      <DialogContent class="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create Schedule</DialogTitle>
        </DialogHeader>

        <form id="schedule-form" @submit.prevent="onSubmit" class="space-y-4">
          <div class="space-y-2">
            <Label for="name">Name</Label>
            <Input
              id="name"
              v-model="nameField.value.value"
              :aria-invalid="nameField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="nameField.errorMessage.value" class="text-sm text-destructive">
              {{ nameField.errorMessage.value }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="function_name">Function</Label>
            <Select v-model="functionNameField.value.value">
              <SelectTrigger>
                <SelectValue placeholder="Select a function" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="fn in functionsStore.functions"
                  :key="fn.name"
                  :value="fn.name"
                >
                  {{ fn.name }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p v-if="selectedFunction?.description" class="text-xs text-muted-foreground">
              {{ selectedFunction.description }}
            </p>
          </div>

          <Field name="method" v-slot="{ field }">
            <div class="space-y-2">
              <Label>Schedule Type</Label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="radio" v-bind="field" value="interval" class="cursor-pointer" />
                  <span class="text-sm">Interval</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="radio" v-bind="field" value="cron" class="cursor-pointer" />
                  <span class="text-sm">Cron</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="radio" v-bind="field" value="once" class="cursor-pointer" />
                  <span class="text-sm">Once</span>
                </label>
              </div>
            </div>
          </Field>

          <Field name="method" v-slot="{ value: method }">
            <!-- Interval Options -->
            <div v-if="method === 'interval'" class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <Label for="value">Value</Label>
                <Input
                  id="value"
                  v-model.number="valueField.value.value"
                  type="number"
                  min="1"
                />
              </div>

              <div class="space-y-2">
                <Label for="unit">Unit</Label>
                <Select v-model="unitField.value.value">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="seconds">Seconds</SelectItem>
                    <SelectItem value="minutes">Minutes</SelectItem>
                    <SelectItem value="hours">Hours</SelectItem>
                    <SelectItem value="days">Days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <!-- Cron Options -->
            <div v-if="method === 'cron'" class="space-y-2">
              <Label for="cron">Cron Expression</Label>
              <Input
                id="cron"
                v-model="cronField.value.value"
                placeholder="0 * * * *"
              />
              <p class="text-xs text-muted-foreground">
                Format: minute hour day_of_month month day_of_week
              </p>
            </div>

            <!-- Once Options -->
            <div v-if="method === 'once'" class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <Label for="date">Date</Label>
                <Input
                  id="date"
                  v-model="dateField.value.value"
                  type="date"
                />
              </div>

              <div class="space-y-2">
                <Label for="time">Time</Label>
                <Input
                  id="time"
                  v-model="timeField.value.value"
                  type="time"
                />
              </div>
            </div>
          </Field>

          <div class="space-y-2">
            <Label for="timezone">Timezone</Label>
            <Input
              id="timezone"
              v-model="timezoneField.value.value"
              placeholder="UTC"
            />
          </div>

          <!-- Input Data -->
          <div class="space-y-2">
            <Label for="input_data">Input Data (JSON)</Label>
            <Textarea
              v-if="loadingSchema"
              id="input_data"
              :rows="8"
              disabled
              class="font-mono text-sm"
              value="Loading schema..."
            />
            <Textarea
              v-else
              id="input_data"
              v-model="inputDataField.value.value"
              :rows="8"
              class="font-mono text-sm"
              spellcheck="false"
              placeholder="{}"
            />
            <p v-if="functionSchema?.input_schema" class="text-xs text-muted-foreground">
              Schema-based template generated. Modify as needed for your use case.
            </p>
            <p v-else-if="values.function_name" class="text-xs text-muted-foreground">
              This function has no input schema. Use an empty object {} or provide custom data.
            </p>
            <p v-else class="text-xs text-muted-foreground">
              Select a function to generate input data template from its schema.
            </p>
          </div>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            @click="showCreateModal = false"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            form="schedule-form"
            :disabled="functionsStore.loading"
          >
            {{ functionsStore.loading ? "Creating..." : "Create Schedule" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
