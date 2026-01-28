<script setup lang="ts">
/**
 * Extensions View
 *
 * Admin page for managing TinyBase extensions.
 * Allows installing, uninstalling, and enabling/disabling extensions.
 */
import { onMounted, ref } from 'vue';
import { useToast } from '../composables/useToast';
import { useForm, useField } from 'vee-validate';
import { api } from '@/api';
import { validationSchemas } from '../composables/useFormValidation';
import Icon from '../components/Icon.vue';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { Puzzle, Settings } from 'lucide-vue-next';
import { Skeleton } from '@/components/ui/skeleton';

interface Extension {
  id: string;
  name: string;
  version: string;
  description: string | null;
  author: string | null;
  repo_url: string;
  is_enabled: boolean;
  installed_at: string;
  updated_at: string;
  update_available: string | null;
}

interface ExtensionListResponse {
  extensions: Extension[];
  total: number;
  limit: number;
  offset: number;
}

interface ExtensionSetting {
  key: string;
  value: string | null;
  value_type: string;
  description: string | null;
}

const toast = useToast();
const loading = ref(true);
const installing = ref(false);

const extensions = ref<Extension[]>([]);
const total = ref(0);

// Install modal
const showInstallModal = ref(false);
const showWarningAccepted = ref(false);

const { handleSubmit, resetForm } = useForm({
  validationSchema: validationSchemas.installExtension,
  initialValues: {
    repo_url: '',
  },
});

const repoUrlField = useField('repo_url');

// Uninstall confirmation
const showUninstallModal = ref(false);
const extensionToUninstall = ref<Extension | null>(null);
const uninstalling = ref(false);

// Settings sheet
const showSettingsSheet = ref(false);
const selectedExtension = ref<Extension | null>(null);
const extensionSettings = ref<ExtensionSetting[]>([]);
const settingsLoading = ref(false);
const settingsSaving = ref(false);
const settingsFormData = ref<Record<string, string | null>>({});

onMounted(async () => {
  await fetchExtensions();
});

async function fetchExtensions() {
  loading.value = true;

  try {
    const response = await api.extensions.listExtensions({
      query: { check_updates: true },
    });
    extensions.value = response.data.extensions;
    total.value = response.data.total;
  } catch (err: any) {
    toast.error(err.error?.detail || 'Failed to load extensions');
  } finally {
    loading.value = false;
  }
}

function openInstallModal() {
  resetForm();
  showWarningAccepted.value = false;
  showInstallModal.value = true;
}

const onSubmit = handleSubmit(async (values) => {
  installing.value = true;

  try {
    await api.extensions.createExtension({
      body: {
        repo_url: values.repo_url.trim(),
      },
    });

    showInstallModal.value = false;
    toast.success('Extension installed successfully. Restart the server to load it.', {
      timeout: 5000,
    });

    await fetchExtensions();
  } catch (err: any) {
    toast.error(err.error?.detail || 'Installation failed');
  } finally {
    installing.value = false;
  }
});

function openUninstallModal(ext: Extension) {
  extensionToUninstall.value = ext;
  showUninstallModal.value = true;
}

async function handleUninstall() {
  if (!extensionToUninstall.value) return;

  uninstalling.value = true;

  try {
    await api.extensions.deleteExtension({
      path: { extension_name: extensionToUninstall.value.name },
    });

    showUninstallModal.value = false;
    toast.success('Extension uninstalled. Restart the server to fully unload it.', {
      timeout: 5000,
    });

    await fetchExtensions();
  } catch (err: any) {
    toast.error(err.error?.detail || 'Uninstall failed');
  } finally {
    uninstalling.value = false;
    extensionToUninstall.value = null;
  }
}

async function toggleEnabled(ext: Extension) {
  try {
    await api.extensions.updateExtension({
      path: { extension_name: ext.name },
      body: {
        is_enabled: !ext.is_enabled,
      },
    });

    ext.is_enabled = !ext.is_enabled;
    toast.success(
      `Extension ${ext.is_enabled ? 'enabled' : 'disabled'}. Restart the server to apply changes.`,
      {
        timeout: 4000,
      }
    );
  } catch (err: any) {
    toast.error(err.error?.detail || 'Failed to update extension');
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

async function openSettingsSheet(ext: Extension) {
  selectedExtension.value = ext;
  settingsLoading.value = true;
  showSettingsSheet.value = true;

  try {
    const response = await api.extensions.getExtensionSettings({
      path: { extension_name: ext.name },
    });
    extensionSettings.value = response.data.settings as ExtensionSetting[];
    
    // Initialize form data
    settingsFormData.value = {};
    for (const setting of extensionSettings.value) {
      settingsFormData.value[setting.key] = setting.value;
    }
  } catch (err: any) {
    toast.error(err.error?.detail || 'Failed to load settings');
    showSettingsSheet.value = false;
  } finally {
    settingsLoading.value = false;
  }
}

async function saveSettings() {
  if (!selectedExtension.value) return;

  settingsSaving.value = true;

  try {
    await api.extensions.updateExtensionSettings({
      path: { extension_name: selectedExtension.value.name },
      body: {
        settings: settingsFormData.value,
      },
    });

    toast.success('Settings saved');
    showSettingsSheet.value = false;
  } catch (err: any) {
    toast.error(err.error?.detail || 'Failed to save settings');
  } finally {
    settingsSaving.value = false;
  }
}

function getInputType(valueType: string): string {
  switch (valueType) {
    case 'int':
    case 'float':
      return 'number';
    case 'bool':
      return 'checkbox';
    default:
      return 'text';
  }
}
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="flex items-start justify-between">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight">Extensions</h1>
        <p class="text-muted-foreground">Manage TinyBase plugins and integrations</p>
      </div>
      <Button @click="openInstallModal"> Install Extension </Button>
    </header>

    <!-- Loading State -->
    <div v-if="loading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card v-for="i in 3" :key="i" class="flex flex-col">
        <CardHeader class="border-b pb-4">
          <Skeleton class="h-6 w-3/4" />
          <Skeleton class="h-4 w-1/4 mt-2" />
        </CardHeader>
        <CardContent class="flex-1 pt-4">
          <Skeleton class="h-4 w-full mb-2" />
          <Skeleton class="h-4 w-5/6" />
        </CardContent>
        <CardFooter class="border-t pt-4">
          <Skeleton class="h-8 w-full" />
        </CardFooter>
      </Card>
    </div>

    <!-- Empty State -->
    <Empty v-else-if="extensions.length === 0">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Puzzle />
        </EmptyMedia>
        <EmptyTitle>No extensions installed</EmptyTitle>
        <EmptyDescription>
          Install extensions from GitHub to add new features to TinyBase.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button @click="openInstallModal"> Install Your First Extension </Button>
      </EmptyContent>
    </Empty>

    <!-- Extensions Grid -->
    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card v-for="ext in extensions" :key="ext.id" class="flex flex-col">
        <CardHeader class="border-b pb-4">
          <div class="flex items-start justify-between gap-2">
            <CardTitle class="text-lg">
              {{ ext.name }}
            </CardTitle>
            <Badge :variant="ext.is_enabled ? 'success' : 'secondary'">
              {{ ext.is_enabled ? 'Enabled' : 'Disabled' }}
            </Badge>
          </div>
          <p class="text-xs text-muted-foreground">v{{ ext.version }}</p>
          <Badge v-if="ext.update_available" variant="outline" class="mt-2 w-fit">
            Update available: v{{ ext.update_available }}
          </Badge>
        </CardHeader>

        <CardContent class="flex-1 pt-4">
          <p v-if="ext.description" class="text-sm mb-4">
            {{ ext.description }}
          </p>
          <p v-else class="text-sm text-muted-foreground mb-4">No description provided.</p>

          <div class="space-y-1 text-xs text-muted-foreground">
            <p v-if="ext.author">By {{ ext.author }}</p>
            <p>Installed {{ formatDate(ext.installed_at) }}</p>
          </div>
        </CardContent>

        <CardFooter class="flex items-center justify-between border-t pt-4">
          <div class="flex items-center gap-2">
            <Switch
              :id="`ext-${ext.id}`"
              :checked="ext.is_enabled"
              @update:checked="toggleEnabled(ext)"
            />
            <Label :for="`ext-${ext.id}`" class="text-sm cursor-pointer">
              {{ ext.is_enabled ? 'Enabled' : 'Disabled' }}
            </Label>
          </div>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" @click="openSettingsSheet(ext)">
              <Settings class="h-3.5 w-3.5 mr-1" />
              Settings
            </Button>
            <Button variant="outline" size="sm" as-child>
              <a :href="ext.repo_url" target="_blank" rel="noopener noreferrer">
                <Icon name="ExternalLink" :size="14" />
                GitHub
              </a>
            </Button>
            <Button variant="outline" size="sm" @click="openUninstallModal(ext)">
              Uninstall
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>

    <!-- Install Modal -->
    <Dialog v-model:open="showInstallModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Install Extension</DialogTitle>
        </DialogHeader>

        <div v-if="!showWarningAccepted">
          <Alert variant="destructive" class="mb-4">
            <AlertTitle>Security Warning</AlertTitle>
            <AlertDescription class="space-y-2">
              <p>
                Extensions can execute arbitrary Python code on your server. Only install extensions
                from sources you trust.
              </p>
              <p class="text-xs">
                Before installing, review the extension's source code on GitHub.
              </p>
            </AlertDescription>
          </Alert>
          <Button variant="secondary" class="w-full" @click="showWarningAccepted = true">
            I understand, continue
          </Button>
        </div>

        <form v-else id="install-form" class="space-y-4" @submit.prevent="onSubmit">
          <div class="space-y-2">
            <Label for="repo_url">GitHub Repository URL</Label>
            <Input
              id="repo_url"
              v-model="repoUrlField.value.value"
              type="url"
              placeholder="https://github.com/username/tinybase-extension"
              :disabled="installing"
              :aria-invalid="repoUrlField.errorMessage.value ? 'true' : undefined"
            />
            <p class="text-xs text-muted-foreground">
              The repository must contain an extension.toml manifest.
            </p>
            <p v-if="repoUrlField.errorMessage.value" class="text-sm text-destructive">
              {{ repoUrlField.errorMessage.value }}
            </p>
          </div>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            :disabled="installing"
            @click="showInstallModal = false"
          >
            Cancel
          </Button>
          <Button type="submit" form="install-form" :disabled="installing">
            {{ installing ? 'Installing...' : 'Install' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Settings Sheet -->
    <Sheet v-model:open="showSettingsSheet">
      <SheetContent class="sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{{ selectedExtension?.name }} Settings</SheetTitle>
          <SheetDescription>
            Configure settings for this extension.
          </SheetDescription>
        </SheetHeader>

        <div v-if="settingsLoading" class="flex items-center justify-center py-8">
          <p class="text-sm text-muted-foreground">Loading settings...</p>
        </div>

        <div v-else-if="extensionSettings.length === 0" class="py-8 text-center">
          <p class="text-sm text-muted-foreground">
            This extension has no configurable settings.
          </p>
        </div>

        <div v-else class="space-y-4 py-4">
          <div v-for="setting in extensionSettings" :key="setting.key" class="space-y-2">
            <Label :for="`setting-${setting.key}`">
              {{ setting.key }}
            </Label>
            
            <!-- Boolean toggle -->
            <div v-if="setting.value_type === 'bool'" class="flex items-center gap-2">
              <Switch
                :id="`setting-${setting.key}`"
                :checked="settingsFormData[setting.key] === 'true'"
                @update:checked="settingsFormData[setting.key] = $event ? 'true' : 'false'"
              />
              <span class="text-sm text-muted-foreground">
                {{ settingsFormData[setting.key] === 'true' ? 'Enabled' : 'Disabled' }}
              </span>
            </div>

            <!-- JSON textarea -->
            <Textarea
              v-else-if="setting.value_type === 'json'"
              :id="`setting-${setting.key}`"
              v-model="settingsFormData[setting.key]"
              :rows="4"
              class="font-mono text-sm"
              spellcheck="false"
            />

            <!-- Number input -->
            <Input
              v-else-if="setting.value_type === 'int' || setting.value_type === 'float'"
              :id="`setting-${setting.key}`"
              v-model="settingsFormData[setting.key]"
              :type="'number'"
              :step="setting.value_type === 'float' ? '0.01' : '1'"
            />

            <!-- Default text input -->
            <Input
              v-else
              :id="`setting-${setting.key}`"
              v-model="settingsFormData[setting.key]"
              type="text"
            />

            <p v-if="setting.description" class="text-xs text-muted-foreground">
              {{ setting.description }}
            </p>
          </div>
        </div>

        <SheetFooter v-if="extensionSettings.length > 0">
          <Button
            type="button"
            variant="ghost"
            :disabled="settingsSaving"
            @click="showSettingsSheet = false"
          >
            Cancel
          </Button>
          <Button :disabled="settingsSaving" @click="saveSettings">
            {{ settingsSaving ? 'Saving...' : 'Save Settings' }}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>

    <!-- Uninstall Confirmation Modal -->
    <Dialog v-model:open="showUninstallModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Uninstall Extension</DialogTitle>
        </DialogHeader>

        <div class="space-y-4">
          <p>
            Are you sure you want to uninstall
            <strong>{{ extensionToUninstall?.name }}</strong
            >?
          </p>
          <p class="text-sm text-muted-foreground">
            This will remove the extension files. Any functions registered by this extension will no
            longer be available after the server restarts.
          </p>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            :disabled="uninstalling"
            @click="showUninstallModal = false"
          >
            Cancel
          </Button>
          <Button variant="destructive" :disabled="uninstalling" @click="handleUninstall">
            {{ uninstalling ? 'Uninstalling...' : 'Uninstall' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
