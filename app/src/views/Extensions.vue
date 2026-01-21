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
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
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
import { Puzzle } from 'lucide-vue-next';

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
    <Card v-if="loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading extensions...</p>
      </CardContent>
    </Card>

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
            <Badge :variant="ext.is_enabled ? 'default' : 'secondary'">
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
