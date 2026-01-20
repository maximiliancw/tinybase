<script setup lang="ts">
/**
 * Settings View
 *
 * Admin page for configuring instance settings.
 */
import { onMounted, ref, reactive, watch, computed, h } from "vue";
import { useToast } from "../composables/useToast";
import { useForm, useField } from "vee-validate";
import { useClipboard } from "@vueuse/core";
import { api } from "../api";
import { useAuthStore } from "../stores/auth";
import { validationSchemas } from "../composables/useFormValidation";
import { formatErrorMessage } from "../composables/useErrorHandling";
import Icon from "../components/Icon.vue";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const toast = useToast();
const authStore = useAuthStore();
const { copy: copyToClipboard, copied } = useClipboard();

// Watch for clipboard copy success
watch(copied, (isCopied) => {
  if (isCopied) {
    toast.success("Token copied to clipboard");
  }
});

interface InstanceSettings {
  instance_name: string;
  allow_public_registration: boolean;
  server_timezone: string;
  token_cleanup_interval: number;
  metrics_collection_interval: number;
  scheduler_function_timeout_seconds: number | null;
  scheduler_max_schedules_per_tick: number | null;
  scheduler_max_concurrent_executions: number | null;
  max_concurrent_functions_per_user: number | null;
  storage_enabled: boolean;
  storage_endpoint: string | null;
  storage_bucket: string | null;
  storage_region: string | null;
  auth_portal_enabled: boolean;
  auth_portal_logo_url: string | null;
  auth_portal_primary_color: string | null;
  auth_portal_background_image_url: string | null;
  auth_portal_login_redirect_url: string | null;
  auth_portal_register_redirect_url: string | null;
  updated_at: string;
}

interface ApplicationToken {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  is_valid: boolean;
}

const loading = ref(true);
const saving = ref(false);

const settings = reactive<InstanceSettings>({
  instance_name: "TinyBase",
  allow_public_registration: true,
  server_timezone: "UTC",
  token_cleanup_interval: 60,
  metrics_collection_interval: 360,
  scheduler_function_timeout_seconds: null,
  scheduler_max_schedules_per_tick: null,
  scheduler_max_concurrent_executions: null,
  max_concurrent_functions_per_user: null,
  storage_enabled: false,
  storage_endpoint: null,
  storage_bucket: null,
  storage_region: null,
  auth_portal_enabled: false,
  auth_portal_logo_url: null,
  auth_portal_primary_color: null,
  auth_portal_background_image_url: null,
  auth_portal_login_redirect_url: null,
  auth_portal_register_redirect_url: null,
  updated_at: "",
});

// Storage credentials (not returned by API, only for updates)
const storageAccessKey = ref("");
const storageSecretKey = ref("");

// Application Tokens
const applicationTokens = ref<ApplicationToken[]>([]);
const loadingTokens = ref(false);
const showCreateTokenForm = ref(false);
const newlyCreatedToken = ref<{
  token: ApplicationToken;
  token_value: string;
} | null>(null);
const creatingToken = ref(false);

const { handleSubmit: handleTokenSubmit, resetForm: resetTokenForm } = useForm({
  validationSchema: validationSchemas.createToken,
  initialValues: {
    name: "",
    description: "",
    expires_days: null as number | null,
  },
});

const tokenNameField = useField("name");
const tokenDescriptionField = useField("description");
const tokenExpiresDaysField = useField("expires_days");

// Common timezones for selection
const commonTimezones = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Singapore",
  "Australia/Sydney",
];

onMounted(async () => {
  await fetchSettings();
  await fetchApplicationTokens();
});

// Disable auth portal when public registration is disabled
watch(
  () => settings.allow_public_registration,
  (enabled) => {
    if (!enabled) {
      settings.auth_portal_enabled = false;
    }
  }
);

// Setup vee-validate form with settings schema for validation
const { handleSubmit, setValues, setFieldValue } = useForm({
  validationSchema: validationSchemas.settings,
  initialValues: settings,
});

// Use useField for redirect URL fields to get proper validation
const {
  value: loginRedirectUrl,
  errorMessage: loginRedirectUrlError,
  handleChange: handleLoginRedirectUrlChange,
  meta: loginRedirectUrlMeta,
} = useField("auth_portal_login_redirect_url", undefined, {
  initialValue: settings.auth_portal_login_redirect_url || "",
  syncVModel: false,
});

const {
  value: registerRedirectUrl,
  errorMessage: registerRedirectUrlError,
  handleChange: handleRegisterRedirectUrlChange,
  meta: registerRedirectUrlMeta,
} = useField("auth_portal_register_redirect_url", undefined, {
  initialValue: settings.auth_portal_register_redirect_url || "",
  syncVModel: false,
});

// Sync field values with settings and form
watch(loginRedirectUrl, (newValue) => {
  settings.auth_portal_login_redirect_url = newValue || null;
  setFieldValue("auth_portal_login_redirect_url", newValue || null);
});

watch(registerRedirectUrl, (newValue) => {
  settings.auth_portal_register_redirect_url = newValue || null;
  setFieldValue("auth_portal_register_redirect_url", newValue || null);
});

// Sync settings back to fields when loaded from API
watch(
  () => settings.auth_portal_login_redirect_url,
  (newValue) => {
    const stringValue = newValue || "";
    if (stringValue !== loginRedirectUrl.value) {
      loginRedirectUrl.value = stringValue;
      setFieldValue("auth_portal_login_redirect_url", newValue || null);
    }
  }
);

watch(
  () => settings.auth_portal_register_redirect_url,
  (newValue) => {
    const stringValue = newValue || "";
    if (stringValue !== registerRedirectUrl.value) {
      registerRedirectUrl.value = stringValue;
      setFieldValue("auth_portal_register_redirect_url", newValue || null);
    }
  }
);

// Update form values when settings change
watch(
  () => settings.auth_portal_enabled,
  (newValue) => {
    setFieldValue("auth_portal_enabled", newValue);
  }
);

// Update all form values when settings are loaded from API
watch(
  () => settings,
  (newSettings) => {
    setValues(newSettings);
    loginRedirectUrl.value = newSettings.auth_portal_login_redirect_url || "";
    registerRedirectUrl.value =
      newSettings.auth_portal_register_redirect_url || "";
  },
  { deep: true }
);

// Generate preview URL with current (unsaved) settings
const previewUrl = computed(() => {
  const params = new URLSearchParams();
  params.append("preview", "true");
  if (settings.auth_portal_logo_url) {
    params.append("logo_url", settings.auth_portal_logo_url);
  }
  if (settings.auth_portal_primary_color) {
    params.append("primary_color", settings.auth_portal_primary_color);
  }
  if (settings.auth_portal_background_image_url) {
    params.append(
      "background_image_url",
      settings.auth_portal_background_image_url
    );
  }
  const token = localStorage.getItem("tb_access_token");
  if (token) {
    params.append("token", token);
  }
  return `/auth/login?${params.toString()}`;
});

function openPreviewInNewTab() {
  window.open(previewUrl.value, "_blank", "noopener,noreferrer");
}

async function fetchSettings() {
  loading.value = true;

  try {
    const response = await api.get("/api/admin/settings");
    Object.assign(settings, response.data);
  } catch (err: any) {
    toast.error(formatErrorMessage(err, "Failed to load settings"));
  } finally {
    loading.value = false;
  }
}

async function fetchApplicationTokens() {
  loadingTokens.value = true;
  try {
    const response = await api.get("/api/admin/application-tokens");
    applicationTokens.value = response.data.tokens;
  } catch (err: any) {
    console.error("Failed to load application tokens:", err);
  } finally {
    loadingTokens.value = false;
  }
}

const onCreateToken = handleTokenSubmit(async (values) => {
  creatingToken.value = true;

  try {
    const payload: Record<string, any> = {
      name: values.name,
    };
    if (values.description) {
      payload.description = values.description;
    }
    if (values.expires_days) {
      payload.expires_days = values.expires_days;
    }

    const response = await api.post("/api/admin/application-tokens", payload);
    newlyCreatedToken.value = response.data;
    await fetchApplicationTokens();

    // Reset form and close modal
    resetTokenForm();
    showCreateTokenForm.value = false;
    toast.success("Application token created successfully");
  } catch (err: any) {
    toast.error(formatErrorMessage(err, "Failed to create token"));
  } finally {
    creatingToken.value = false;
  }
});

async function revokeApplicationToken(tokenId: string) {
  if (
    !confirm(
      "Are you sure you want to revoke this token? It will no longer be usable."
    )
  ) {
    return;
  }

  try {
    await api.delete(`/api/admin/application-tokens/${tokenId}`);
    await fetchApplicationTokens();
    if (newlyCreatedToken.value?.token.id === tokenId) {
      newlyCreatedToken.value = null;
    }
    toast.success("Token revoked successfully");
  } catch (err: any) {
    toast.error(formatErrorMessage(err, "Failed to revoke token"));
  }
}

async function toggleTokenActive(tokenId: string, currentStatus: boolean) {
  try {
    await api.patch(`/api/admin/application-tokens/${tokenId}`, {
      is_active: !currentStatus,
    });
    await fetchApplicationTokens();
    toast.success(
      `Token ${!currentStatus ? "activated" : "deactivated"} successfully`
    );
  } catch (err: any) {
    toast.error(formatErrorMessage(err, "Failed to update token"));
  }
}

function copyTokenToClipboard(tokenValue: string) {
  copyToClipboard(tokenValue);
}

function dismissNewToken() {
  newlyCreatedToken.value = null;
}

const saveSettings = handleSubmit(async (values) => {
  saving.value = true;

  try {
    const payload: Record<string, any> = {
      instance_name: values.instance_name,
      allow_public_registration: values.allow_public_registration,
      server_timezone: values.server_timezone,
      token_cleanup_interval: values.token_cleanup_interval,
      metrics_collection_interval: values.metrics_collection_interval,
      scheduler_function_timeout_seconds:
        values.scheduler_function_timeout_seconds,
      scheduler_max_schedules_per_tick: values.scheduler_max_schedules_per_tick,
      scheduler_max_concurrent_executions:
        values.scheduler_max_concurrent_executions,
      max_concurrent_functions_per_user: values.max_concurrent_functions_per_user,
      storage_enabled: values.storage_enabled,
      storage_endpoint: values.storage_endpoint,
      storage_bucket: values.storage_bucket,
      storage_region: values.storage_region,
      auth_portal_enabled: values.auth_portal_enabled,
      auth_portal_logo_url: values.auth_portal_logo_url,
      auth_portal_primary_color: values.auth_portal_primary_color,
      auth_portal_background_image_url: values.auth_portal_background_image_url,
      auth_portal_login_redirect_url: values.auth_portal_login_redirect_url,
      auth_portal_register_redirect_url:
        values.auth_portal_register_redirect_url,
    };

    // Only include credentials if they're filled in
    if (storageAccessKey.value) {
      payload.storage_access_key = storageAccessKey.value;
    }
    if (storageSecretKey.value) {
      payload.storage_secret_key = storageSecretKey.value;
    }

    const response = await api.patch("/api/admin/settings", payload);
    Object.assign(settings, response.data);

    // Update form values after successful save
    setValues(response.data);
    loginRedirectUrl.value = response.data.auth_portal_login_redirect_url || "";
    registerRedirectUrl.value =
      response.data.auth_portal_register_redirect_url || "";

    // Clear credentials after save
    storageAccessKey.value = "";
    storageSecretKey.value = "";

    toast.success("Settings saved successfully");
    authStore.fetchInstanceInfo(); // Update instance name in header
  } catch (err: any) {
    toast.error(formatErrorMessage(err, "Failed to save settings"));
  } finally {
    saving.value = false;
  }
});
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Settings</h1>
      <p class="text-muted-foreground">Configure your TinyBase instance</p>
    </header>

    <!-- Loading State -->
    <Card v-if="loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading settings...</p>
      </CardContent>
    </Card>

    <form v-else @submit.prevent="saveSettings" class="space-y-6">
      <!-- General Settings -->
      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2">
              <Label for="instance_name">Instance Name</Label>
              <Input
                id="instance_name"
                v-model="settings.instance_name"
              />
            </div>

            <div class="space-y-2">
              <Label for="server_timezone">Server Timezone</Label>
              <Select v-model="settings.server_timezone">
                <SelectTrigger>
                  <SelectValue placeholder="Select timezone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="tz in commonTimezones" :key="tz" :value="tz">
                    {{ tz }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2">
              <Label for="token_cleanup_interval">Token Cleanup Interval (minutes)</Label>
              <Input
                id="token_cleanup_interval"
                v-model.number="settings.token_cleanup_interval"
                type="number"
                min="1"
              />
            </div>

            <div class="space-y-2">
              <Label for="metrics_collection_interval">Metrics Collection Interval (minutes)</Label>
              <Input
                id="metrics_collection_interval"
                v-model.number="settings.metrics_collection_interval"
                type="number"
                min="1"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Authentication Settings -->
      <Card>
        <CardHeader>
          <CardTitle>Authentication</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="flex items-center space-x-2">
            <Switch
              id="allow_public_registration"
              :checked="settings.allow_public_registration"
              @update:checked="settings.allow_public_registration = $event"
            />
            <Label for="allow_public_registration" class="cursor-pointer">
              Allow public registration
            </Label>
          </div>

          <div v-if="settings.allow_public_registration" class="space-y-4 pl-6 border-l-2 border-muted">
            <div class="flex items-center space-x-2">
              <Switch
                id="auth_portal_enabled"
                :checked="settings.auth_portal_enabled"
                @update:checked="settings.auth_portal_enabled = $event"
              />
              <Label for="auth_portal_enabled" class="cursor-pointer">
                Enable custom auth portal
              </Label>
            </div>

            <div v-if="settings.auth_portal_enabled" class="space-y-4 pl-6 border-l-2 border-muted">
              <div class="space-y-2">
                <Label for="auth_portal_logo_url">Logo URL</Label>
                <Input
                  id="auth_portal_logo_url"
                  v-model="settings.auth_portal_logo_url"
                  placeholder="https://example.com/logo.png"
                />
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_primary_color">Primary Color</Label>
                <Input
                  id="auth_portal_primary_color"
                  v-model="settings.auth_portal_primary_color"
                  type="color"
                />
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_background_image_url">Background Image URL</Label>
                <Input
                  id="auth_portal_background_image_url"
                  v-model="settings.auth_portal_background_image_url"
                  placeholder="https://example.com/bg.jpg"
                />
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_login_redirect_url">Login Redirect URL</Label>
                <Input
                  id="auth_portal_login_redirect_url"
                  v-model="loginRedirectUrl"
                  placeholder="https://example.com/dashboard"
                  :aria-invalid="loginRedirectUrlError ? 'true' : undefined"
                />
                <p v-if="loginRedirectUrlError" class="text-sm text-destructive">
                  {{ loginRedirectUrlError }}
                </p>
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_register_redirect_url">Register Redirect URL</Label>
                <Input
                  id="auth_portal_register_redirect_url"
                  v-model="registerRedirectUrl"
                  placeholder="https://example.com/onboarding"
                  :aria-invalid="registerRedirectUrlError ? 'true' : undefined"
                />
                <p v-if="registerRedirectUrlError" class="text-sm text-destructive">
                  {{ registerRedirectUrlError }}
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                @click="openPreviewInNewTab"
              >
                <Icon name="ExternalLink" :size="16" />
                Preview Auth Portal
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Scheduler & Rate Limiting Settings -->
      <Card>
        <CardHeader>
          <CardTitle>Scheduler & Rate Limiting</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2">
              <Label for="scheduler_function_timeout_seconds">
                Function Timeout (seconds)
              </Label>
              <Input
                id="scheduler_function_timeout_seconds"
                v-model.number="settings.scheduler_function_timeout_seconds"
                type="number"
                min="1"
                placeholder="null = no limit"
              />
            </div>

            <div class="space-y-2">
              <Label for="scheduler_max_schedules_per_tick">
                Max Schedules Per Tick
              </Label>
              <Input
                id="scheduler_max_schedules_per_tick"
                v-model.number="settings.scheduler_max_schedules_per_tick"
                type="number"
                min="1"
                placeholder="null = no limit"
              />
            </div>

            <div class="space-y-2">
              <Label for="scheduler_max_concurrent_executions">
                Max Concurrent Executions
              </Label>
              <Input
                id="scheduler_max_concurrent_executions"
                v-model.number="settings.scheduler_max_concurrent_executions"
                type="number"
                min="1"
                placeholder="null = no limit"
              />
            </div>

            <div class="space-y-2">
              <Label for="max_concurrent_functions_per_user">
                Max Concurrent Functions Per User
              </Label>
              <Input
                id="max_concurrent_functions_per_user"
                v-model.number="settings.max_concurrent_functions_per_user"
                type="number"
                min="1"
                placeholder="null = no limit"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Storage Settings -->
      <Card>
        <CardHeader>
          <CardTitle>Storage (S3-Compatible)</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="flex items-center space-x-2">
            <Switch
              id="storage_enabled"
              :checked="settings.storage_enabled"
              @update:checked="settings.storage_enabled = $event"
            />
            <Label for="storage_enabled" class="cursor-pointer">
              Enable S3 storage
            </Label>
          </div>

          <div v-if="settings.storage_enabled" class="space-y-4 pl-6 border-l-2 border-muted">
            <div class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <Label for="storage_endpoint">Endpoint</Label>
                <Input
                  id="storage_endpoint"
                  v-model="settings.storage_endpoint"
                  placeholder="https://s3.amazonaws.com"
                />
              </div>

              <div class="space-y-2">
                <Label for="storage_bucket">Bucket</Label>
                <Input
                  id="storage_bucket"
                  v-model="settings.storage_bucket"
                  placeholder="my-bucket"
                />
              </div>

              <div class="space-y-2">
                <Label for="storage_region">Region</Label>
                <Input
                  id="storage_region"
                  v-model="settings.storage_region"
                  placeholder="us-east-1"
                />
              </div>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <Label for="storage_access_key">Access Key (leave empty to keep current)</Label>
                <Input
                  id="storage_access_key"
                  v-model="storageAccessKey"
                  type="password"
                  autocomplete="off"
                />
              </div>

              <div class="space-y-2">
                <Label for="storage_secret_key">Secret Key (leave empty to keep current)</Label>
                <Input
                  id="storage_secret_key"
                  v-model="storageSecretKey"
                  type="password"
                  autocomplete="off"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Application Tokens -->
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <div>
              <CardTitle>Application Tokens</CardTitle>
              <CardDescription class="mt-1">
                Create API tokens for programmatic access
              </CardDescription>
            </div>
            <Button
              type="button"
              @click="showCreateTokenForm = true"
            >
              <Icon name="Plus" :size="16" />
              Create Token
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <!-- New Token Alert -->
          <Alert v-if="newlyCreatedToken" class="mb-4">
            <AlertDescription class="space-y-2">
              <p class="font-semibold">Token created successfully!</p>
              <p class="text-sm">
                Make sure to copy your token now. You won't be able to see it again.
              </p>
              <div class="flex items-center gap-2">
                <Input
                  :value="newlyCreatedToken.token_value"
                  readonly
                  class="font-mono text-sm"
                />
                <Button
                  type="button"
                  size="sm"
                  @click="copyTokenToClipboard(newlyCreatedToken.token_value)"
                >
                  <Icon name="Copy" :size="14" />
                  Copy
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  @click="dismissNewToken"
                >
                  Dismiss
                </Button>
              </div>
            </AlertDescription>
          </Alert>

          <div v-if="loadingTokens" class="flex items-center justify-center py-10">
            <p class="text-sm text-muted-foreground">Loading tokens...</p>
          </div>

          <div v-else-if="applicationTokens.length === 0" class="text-center py-10">
            <p class="text-sm text-muted-foreground">No application tokens yet</p>
          </div>

          <div v-else class="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="token in applicationTokens" :key="token.id">
                  <TableCell>{{ token.name }}</TableCell>
                  <TableCell>
                    <span class="text-sm text-muted-foreground">
                      {{ token.description || "-" }}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      :variant="
                        !token.is_valid
                          ? 'destructive'
                          : token.is_active
                          ? 'default'
                          : 'secondary'
                      "
                    >
                      {{
                        !token.is_valid
                          ? "Invalid"
                          : token.is_active
                          ? "Active"
                          : "Inactive"
                      }}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span class="text-sm">
                      {{ new Date(token.created_at).toLocaleDateString() }}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span class="text-sm">
                      {{ token.expires_at ? new Date(token.expires_at).toLocaleDateString() : "Never" }}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span class="text-sm">
                      {{ token.last_used_at ? new Date(token.last_used_at).toLocaleDateString() : "Never" }}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div class="flex gap-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        @click="toggleTokenActive(token.id, token.is_active)"
                      >
                        {{ token.is_active ? "Deactivate" : "Activate" }}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        @click="revokeApplicationToken(token.id)"
                      >
                        Revoke
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <!-- Save Footer -->
      <div class="flex justify-end gap-2 sticky bottom-0 bg-background py-4 border-t">
        <Button
          type="submit"
          :disabled="saving"
        >
          {{ saving ? "Saving..." : "Save Settings" }}
        </Button>
      </div>
    </form>

    <!-- Create Token Modal -->
    <Dialog v-model:open="showCreateTokenForm">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Application Token</DialogTitle>
        </DialogHeader>

        <form @submit.prevent="onCreateToken" class="space-y-4">
          <div class="space-y-2">
            <Label for="token_name">Name</Label>
            <Input
              id="token_name"
              v-model="tokenNameField.value.value"
              placeholder="My Application"
              :aria-invalid="tokenNameField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="tokenNameField.errorMessage.value" class="text-sm text-destructive">
              {{ tokenNameField.errorMessage.value }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="token_description">Description (optional)</Label>
            <Textarea
              id="token_description"
              v-model="tokenDescriptionField.value.value"
              placeholder="What this token is used for..."
              :rows="3"
            />
          </div>

          <div class="space-y-2">
            <Label for="token_expires_days">Expires in (days, optional)</Label>
            <Input
              id="token_expires_days"
              v-model.number="tokenExpiresDaysField.value.value"
              type="number"
              min="1"
              placeholder="Leave empty for no expiration"
            />
          </div>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            @click="showCreateTokenForm = false"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            @click="onCreateToken"
            :disabled="creatingToken"
          >
            {{ creatingToken ? "Creating..." : "Create Token" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
