<script setup lang="ts">
/**
 * Settings View
 *
 * Admin page for configuring instance settings.
 */
import { onMounted, onBeforeUnmount, ref, watch, computed, h } from "vue";
import { useToast } from "../composables/useToast";
import { useForm, useField } from "vee-validate";
import { useClipboard } from "@vueuse/core";
import { onBeforeRouteLeave } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useSettingsStore } from "../stores/settings";
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
const settingsStore = useSettingsStore();
const { copy: copyToClipboard, copied } = useClipboard();

// Watch for clipboard copy success
watch(copied, (isCopied) => {
  if (isCopied) {
    toast.success("Token copied to clipboard");
  }
});

// Local UI state
const saving = ref(false);
const storageAccessKey = ref("");
const storageSecretKey = ref("");
const showCreateTokenForm = ref(false);
const newlyCreatedToken = ref<{
  token: any;
  token_value: string;
} | null>(null);
const creatingToken = ref(false);

// Computed properties from store
const loading = computed(() => settingsStore.loading);
const applicationTokens = computed(() => settingsStore.applicationTokens);
const loadingTokens = computed(() => settingsStore.loadingTokens);

// Setup vee-validate form
const { handleSubmit, values, setValues, resetForm, meta } = useForm({
  validationSchema: validationSchemas.settings,
  initialValues: {
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
  },
});

// Load settings from store when available
watch(() => settingsStore.settings, (settings) => {
  if (settings) {
    setValues(settings);
  }
}, { immediate: true });

// Warn about unsaved changes when navigating away
onBeforeRouteLeave((to, from, next) => {
  if (meta.value.dirty && !saving.value) {
    const answer = window.confirm(
      "You have unsaved changes. Are you sure you want to leave?"
    );
    if (answer) {
      next();
    } else {
      next(false);
    }
  } else {
    next();
  }
});

// Warn about unsaved changes when closing/refreshing browser
const handleBeforeUnload = (e: BeforeUnloadEvent) => {
  if (meta.value.dirty && !saving.value) {
    e.preventDefault();
    e.returnValue = "";
  }
};

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
  await settingsStore.fetchSettings();
  await settingsStore.fetchApplicationTokens();
  window.addEventListener("beforeunload", handleBeforeUnload);
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", handleBeforeUnload);
});

// Use useField for fields that need validation
const loginRedirectUrlField = useField("auth_portal_login_redirect_url");
const registerRedirectUrlField = useField("auth_portal_register_redirect_url");

// Generate preview URL with current form values
const previewUrl = computed(() => {
  const params = new URLSearchParams();
  params.append("preview", "true");
  if (values.auth_portal_logo_url) {
    params.append("logo_url", values.auth_portal_logo_url);
  }
  if (values.auth_portal_primary_color) {
    params.append("primary_color", values.auth_portal_primary_color);
  }
  if (values.auth_portal_background_image_url) {
    params.append(
      "background_image_url",
      values.auth_portal_background_image_url
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


const onCreateToken = handleTokenSubmit(async (values) => {
  creatingToken.value = true;

  try {
    const payload: {
      name: string;
      description?: string;
      expires_days?: number;
    } = {
      name: values.name,
    };
    if (values.description) {
      payload.description = values.description;
    }
    if (values.expires_days) {
      payload.expires_days = values.expires_days;
    }

    const response = await settingsStore.createApplicationToken(payload);
    newlyCreatedToken.value = response;

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
    await settingsStore.revokeApplicationToken(tokenId);
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
    await settingsStore.updateApplicationToken(tokenId, {
      is_active: !currentStatus,
    });
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

const saveSettings = handleSubmit(async (formValues) => {
  saving.value = true;

  try {
    const payload: any = { ...formValues };

    // Only include credentials if they're filled in
    if (storageAccessKey.value) {
      payload.storage_access_key = storageAccessKey.value;
    }
    if (storageSecretKey.value) {
      payload.storage_secret_key = storageSecretKey.value;
    }

    await settingsStore.updateSettings(payload);

    // Clear credentials after save
    storageAccessKey.value = "";
    storageSecretKey.value = "";

    // Reset form dirty state since changes are saved
    if (settingsStore.settings) {
      resetForm({ values: settingsStore.settings });
    }

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
      <h1 class="text-3xl font-bold tracking-tight">
        Settings
      </h1>
      <p class="text-muted-foreground">
        Configure your TinyBase instance
      </p>
    </header>

    <!-- Loading State -->
    <Card v-if="loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">
          Loading settings...
        </p>
      </CardContent>
    </Card>

    <form
      v-else
      class="space-y-6"
      @submit.prevent="saveSettings"
    >
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
                v-model="values.instance_name"
              />
            </div>

            <div class="space-y-2">
              <Label for="server_timezone">Server Timezone</Label>
              <Select v-model="values.server_timezone">
                <SelectTrigger>
                  <SelectValue placeholder="Select timezone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="tz in commonTimezones"
                    :key="tz"
                    :value="tz"
                  >
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
                v-model.number="values.token_cleanup_interval"
                type="number"
                min="1"
              />
            </div>

            <div class="space-y-2">
              <Label for="metrics_collection_interval">Metrics Collection Interval (minutes)</Label>
              <Input
                id="metrics_collection_interval"
                v-model.number="values.metrics_collection_interval"
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
              :checked="values.allow_public_registration"
              @update:checked="values.allow_public_registration = $event"
            />
            <Label
              for="allow_public_registration"
              class="cursor-pointer"
            >
              Allow public registration
            </Label>
          </div>

          <div
            v-if="values.allow_public_registration"
            class="space-y-4 pl-6 border-l-2 border-muted"
          >
            <div class="flex items-center space-x-2">
              <Switch
                id="auth_portal_enabled"
                :checked="values.auth_portal_enabled"
                @update:checked="values.auth_portal_enabled = $event"
              />
              <Label
                for="auth_portal_enabled"
                class="cursor-pointer"
              >
                Enable custom auth portal
              </Label>
            </div>

            <div
              v-if="values.auth_portal_enabled"
              class="space-y-4 pl-6 border-l-2 border-muted"
            >
              <div class="space-y-2">
                <Label for="auth_portal_logo_url">Logo URL</Label>
                <Input
                  id="auth_portal_logo_url"
                  v-model="values.auth_portal_logo_url"
                  placeholder="https://example.com/logo.png"
                />
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_primary_color">Primary Color</Label>
                <Input
                  id="auth_portal_primary_color"
                  v-model="values.auth_portal_primary_color"
                  type="color"
                />
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_background_image_url">Background Image URL</Label>
                <Input
                  id="auth_portal_background_image_url"
                  v-model="values.auth_portal_background_image_url"
                  placeholder="https://example.com/bg.jpg"
                />
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_login_redirect_url">Login Redirect URL</Label>
                <Input
                  id="auth_portal_login_redirect_url"
                  v-model="loginRedirectUrlField.value.value"
                  placeholder="https://example.com/dashboard"
                  :aria-invalid="loginRedirectUrlField.errorMessage.value ? 'true' : undefined"
                />
                <p
                  v-if="loginRedirectUrlField.errorMessage.value"
                  class="text-sm text-destructive"
                >
                  {{ loginRedirectUrlField.errorMessage.value }}
                </p>
              </div>

              <div class="space-y-2">
                <Label for="auth_portal_register_redirect_url">Register Redirect URL</Label>
                <Input
                  id="auth_portal_register_redirect_url"
                  v-model="registerRedirectUrlField.value.value"
                  placeholder="https://example.com/onboarding"
                  :aria-invalid="registerRedirectUrlField.errorMessage.value ? 'true' : undefined"
                />
                <p
                  v-if="registerRedirectUrlField.errorMessage.value"
                  class="text-sm text-destructive"
                >
                  {{ registerRedirectUrlField.errorMessage.value }}
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                @click="openPreviewInNewTab"
              >
                <Icon
                  name="ExternalLink"
                  :size="16"
                />
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
                v-model.number="values.scheduler_function_timeout_seconds"
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
                v-model.number="values.scheduler_max_schedules_per_tick"
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
                v-model.number="values.scheduler_max_concurrent_executions"
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
                v-model.number="values.max_concurrent_functions_per_user"
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
              :checked="values.storage_enabled"
              @update:checked="values.storage_enabled = $event"
            />
            <Label
              for="storage_enabled"
              class="cursor-pointer"
            >
              Enable S3 storage
            </Label>
          </div>

          <div
            v-if="values.storage_enabled"
            class="space-y-4 pl-6 border-l-2 border-muted"
          >
            <div class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <Label for="storage_endpoint">Endpoint</Label>
                <Input
                  id="storage_endpoint"
                  v-model="values.storage_endpoint"
                  placeholder="https://s3.amazonaws.com"
                />
              </div>

              <div class="space-y-2">
                <Label for="storage_bucket">Bucket</Label>
                <Input
                  id="storage_bucket"
                  v-model="values.storage_bucket"
                  placeholder="my-bucket"
                />
              </div>

              <div class="space-y-2">
                <Label for="storage_region">Region</Label>
                <Input
                  id="storage_region"
                  v-model="values.storage_region"
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
              <Icon
                name="Plus"
                :size="16"
              />
              Create Token
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <!-- New Token Alert -->
          <Alert
            v-if="newlyCreatedToken"
            class="mb-4"
          >
            <AlertDescription class="space-y-2">
              <p class="font-semibold">
                Token created successfully!
              </p>
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
                  <Icon
                    name="Copy"
                    :size="14"
                  />
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

          <div
            v-if="loadingTokens"
            class="flex items-center justify-center py-10"
          >
            <p class="text-sm text-muted-foreground">
              Loading tokens...
            </p>
          </div>

          <div
            v-else-if="applicationTokens.length === 0"
            class="text-center py-10"
          >
            <p class="text-sm text-muted-foreground">
              No application tokens yet
            </p>
          </div>

          <div
            v-else
            class="rounded-lg border"
          >
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
                <TableRow
                  v-for="token in applicationTokens"
                  :key="token.id"
                >
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

        <form
          class="space-y-4"
          @submit.prevent="onCreateToken"
        >
          <div class="space-y-2">
            <Label for="token_name">Name</Label>
            <Input
              id="token_name"
              v-model="tokenNameField.value.value"
              placeholder="My Application"
              :aria-invalid="tokenNameField.errorMessage.value ? 'true' : undefined"
            />
            <p
              v-if="tokenNameField.errorMessage.value"
              class="text-sm text-destructive"
            >
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
            :disabled="creatingToken"
            @click="onCreateToken"
          >
            {{ creatingToken ? "Creating..." : "Create Token" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
