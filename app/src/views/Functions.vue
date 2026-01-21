<script setup lang="ts">
/**
 * Functions View
 *
 * View and invoke registered functions.
 */
import { onMounted, ref, computed, h } from 'vue';
import { useToast } from '../composables/useToast';
import {
  useFunctionsStore,
  generateTemplateFromSchema,
  type FunctionInfo,
} from '../stores/functions';
import { useAuthStore } from '../stores/auth';
import DataTable from '../components/DataTable.vue';
import { Card, CardContent } from '@/components/ui/card';
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
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const toast = useToast();
const functionsStore = useFunctionsStore();
const authStore = useAuthStore();

const showCallModal = ref(false);
const selectedFunction = ref<FunctionInfo | null>(null);
const callPayload = ref('{}');
const callResult = ref<any>(null);
const loadingSchema = ref(false);

// Upload function state
const showUploadModal = ref(false);
const uploadFilename = ref('');
const uploadContent = ref('');
const uploadNotes = ref('');
const uploading = ref(false);

// Version history state
const showVersionsModal = ref(false);
const selectedFunctionVersions = ref<any[]>([]);
const loadingVersions = ref(false);

onMounted(async () => {
  if (authStore.isAdmin) {
    await functionsStore.fetchAdminFunctions();
  } else {
    await functionsStore.fetchFunctions();
  }
});

async function openCallModal(fn: FunctionInfo) {
  selectedFunction.value = fn;
  callResult.value = null;
  showCallModal.value = true;

  // Fetch schema and generate template
  loadingSchema.value = true;
  try {
    const schema = await functionsStore.fetchFunctionSchema(fn.name);
    if (schema?.input_schema) {
      const template = generateTemplateFromSchema(schema.input_schema);
      callPayload.value = JSON.stringify(template, null, 2);
    } else {
      callPayload.value = '{}';
    }
  } catch {
    callPayload.value = '{}';
  } finally {
    loadingSchema.value = false;
  }
}

async function handleCall() {
  if (!selectedFunction.value) return;

  callResult.value = null;

  try {
    const payload = JSON.parse(callPayload.value);
    const result = await functionsStore.callFunction(selectedFunction.value.name, payload);
    callResult.value = result;
    if (result.status === 'succeeded') {
      toast.success(`Function "${selectedFunction.value.name}" executed successfully`);
    } else {
      toast.error(
        `Function "${selectedFunction.value.name}" failed: ${
          result.error_message || 'Unknown error'
        }`
      );
    }
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || err.message || 'Call failed';
    toast.error(errorMsg);
    callResult.value = {
      status: 'failed',
      error_type: 'ExecutionError',
      error_message: errorMsg,
    };
  }
}

function openUploadModal() {
  uploadFilename.value = '';
  uploadContent.value = '';
  uploadNotes.value = '';
  showUploadModal.value = true;
}

async function handleUpload() {
  if (!uploadFilename.value || !uploadContent.value) {
    toast.error('Filename and content are required');
    return;
  }

  // Validate filename
  if (!uploadFilename.value.endsWith('.py')) {
    toast.error('Filename must end with .py');
    return;
  }

  uploading.value = true;
  try {
    const result = await functionsStore.uploadFunction(
      uploadFilename.value,
      uploadContent.value,
      uploadNotes.value || undefined
    );

    toast.success(
      result.is_new_version
        ? `Function "${result.function_name}" updated successfully`
        : `Function "${result.function_name}" created successfully`
    );

    // Show warnings if any
    if (result.warnings && result.warnings.length > 0) {
      result.warnings.forEach((warning: string) => {
        toast.warning(warning);
      });
    }

    showUploadModal.value = false;
    await functionsStore.fetchAdminFunctions();
  } catch (err: any) {
    toast.error(err.response?.data?.detail || 'Failed to upload function');
  } finally {
    uploading.value = false;
  }
}

async function openVersionsModal(fn: FunctionInfo) {
  selectedFunction.value = fn;
  showVersionsModal.value = true;
  loadingVersions.value = true;

  try {
    selectedFunctionVersions.value = await functionsStore.fetchFunctionVersions(fn.name);
  } catch (err) {
    toast.error('Failed to load version history');
  } finally {
    loadingVersions.value = false;
  }
}

function getAuthBadgeVariant(auth: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (auth) {
    case 'public':
      return 'default';
    case 'auth':
      return 'secondary';
    case 'admin':
      return 'destructive';
    default:
      return 'outline';
  }
}

const displayFunctions = () => {
  return authStore.isAdmin ? functionsStore.adminFunctions : functionsStore.functions;
};

const functionColumns = computed(() => {
  const columns: any[] = [
    {
      key: 'name',
      label: 'Name',
      render: (value: any) => h('code', { class: 'text-sm' }, value),
    },
    {
      key: 'description',
      label: 'Description',
      render: (value: any) => h('span', { class: 'text-sm text-muted-foreground' }, value || '-'),
    },
    {
      key: 'auth',
      label: 'Auth',
      render: (value: any) => h(Badge, { variant: getAuthBadgeVariant(value) }, () => value),
    },
    {
      key: 'tags',
      label: 'Tags',
      render: (value: any, row: any) => {
        if (!row.tags || row.tags.length === 0) {
          return h('span', { class: 'text-sm text-muted-foreground' }, '-');
        }
        return h(
          'div',
          { class: 'flex gap-1 flex-wrap' },
          row.tags.map((tag: string) => h(Badge, { variant: 'outline' }, () => tag))
        );
      },
    },
  ];

  if (authStore.isAdmin) {
    columns.push({
      key: 'module',
      label: 'Module',
      render: (value: any) => h('span', { class: 'text-sm text-muted-foreground' }, value),
    });
  }

  const actions: any[] = [
    {
      label: 'Call',
      action: (row: any) => openCallModal(row),
      variant: 'default' as const,
    },
  ];

  // Add "Versions" action for admins
  if (authStore.isAdmin) {
    actions.push({
      label: 'Versions',
      action: (row: any) => openVersionsModal(row),
      variant: 'secondary' as const,
    });
  }

  columns.push({
    key: 'actions',
    label: 'Actions',
    actions,
  });

  return columns;
});
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="flex items-start justify-between">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight">Functions</h1>
        <p class="text-muted-foreground">Registered server-side functions</p>
      </div>
      <Button v-if="authStore.isAdmin" @click="openUploadModal"> Upload Function </Button>
    </header>

    <!-- Loading State -->
    <Card v-if="functionsStore.loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading functions...</p>
      </CardContent>
    </Card>

    <!-- Functions Table -->
    <Card v-else>
      <DataTable
        :data="displayFunctions()"
        :columns="functionColumns"
        :page-size="20"
        search-placeholder="Search functions..."
        empty-message="No functions registered. Define functions in functions.py using the @register decorator."
      />
    </Card>

    <!-- Call Function Modal -->
    <Dialog v-model:open="showCallModal">
      <DialogContent class="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            Call: <code class="text-sm">{{ selectedFunction?.name }}</code>
          </DialogTitle>
        </DialogHeader>

        <div class="space-y-4">
          <p v-if="selectedFunction?.description" class="text-sm text-muted-foreground">
            {{ selectedFunction.description }}
          </p>

          <form class="space-y-4" @submit.prevent="handleCall">
            <div class="space-y-2">
              <Label for="payload">Payload (JSON)</Label>
              <Textarea
                v-if="loadingSchema"
                id="payload"
                :rows="8"
                disabled
                class="font-mono text-sm"
                value="Loading schema..."
              />
              <Textarea
                v-else
                id="payload"
                v-model="callPayload"
                :rows="8"
                class="font-mono text-sm"
                spellcheck="false"
              />
            </div>

            <Button type="submit" :disabled="functionsStore.loading || loadingSchema">
              {{ functionsStore.loading ? 'Executing...' : 'Execute' }}
            </Button>
          </form>

          <!-- Result Display -->
          <div v-if="callResult" class="space-y-3 rounded-lg border p-4">
            <div class="flex items-center gap-2">
              <h4 class="font-semibold">Result</h4>
              <Badge :variant="callResult.status === 'succeeded' ? 'success' : 'destructive'">
                {{ callResult.status }}
              </Badge>
              <span v-if="callResult.duration_ms" class="text-xs text-muted-foreground">
                Duration: {{ callResult.duration_ms }}ms
              </span>
            </div>
            <pre v-if="callResult.result" class="rounded bg-muted p-3 text-sm overflow-x-auto">{{
              JSON.stringify(callResult.result, null, 2)
            }}</pre>
            <div v-if="callResult.error_message" class="text-sm text-destructive">
              <strong>{{ callResult.error_type }}:</strong>
              {{ callResult.error_message }}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Upload Function Modal -->
    <Dialog v-model:open="showUploadModal">
      <DialogContent class="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Upload Function</DialogTitle>
        </DialogHeader>

        <form class="space-y-4" @submit.prevent="handleUpload">
          <div class="space-y-2">
            <Label for="upload-filename">Filename</Label>
            <Input
              id="upload-filename"
              v-model="uploadFilename"
              placeholder="my_function.py"
              required
            />
            <p class="text-xs text-muted-foreground">
              Must end with .py and be a valid Python identifier.
            </p>
          </div>

          <div class="space-y-2">
            <Label for="upload-content">Function Code</Label>
            <Textarea
              id="upload-content"
              v-model="uploadContent"
              :rows="15"
              class="font-mono text-sm"
              spellcheck="false"
              required
              placeholder='# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register

@register(name="my_function", description="My function")
def my_function(client, payload):
    return {"result": "success"}'
            />
          </div>

          <div class="space-y-2">
            <Label for="upload-notes">Deployment Notes (optional)</Label>
            <Textarea
              id="upload-notes"
              v-model="uploadNotes"
              :rows="3"
              placeholder="What changed in this version..."
            />
          </div>
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="ghost"
            :disabled="uploading"
            @click="showUploadModal = false"
          >
            Cancel
          </Button>
          <Button type="submit" form="upload-form" :disabled="uploading" @click="handleUpload">
            {{ uploading ? 'Uploading...' : 'Upload' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Version History Modal -->
    <Dialog v-model:open="showVersionsModal">
      <DialogContent class="max-w-5xl">
        <DialogHeader>
          <DialogTitle>
            Version History: <code class="text-sm">{{ selectedFunction?.name }}</code>
          </DialogTitle>
        </DialogHeader>

        <div v-if="loadingVersions" class="flex items-center justify-center py-10">
          <p class="text-sm text-muted-foreground">Loading versions...</p>
        </div>

        <div v-else-if="selectedFunctionVersions.length === 0" class="py-10 text-center">
          <p class="text-sm text-muted-foreground">No version history available.</p>
        </div>

        <div v-else class="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Version ID</TableHead>
                <TableHead>Content Hash</TableHead>
                <TableHead>Deployed By</TableHead>
                <TableHead>Deployed At</TableHead>
                <TableHead>Executions</TableHead>
                <TableHead>Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="version in selectedFunctionVersions" :key="version.id">
                <TableCell>
                  <code class="text-xs">{{ version.id.substring(0, 8) }}</code>
                </TableCell>
                <TableCell>
                  <code class="text-xs">{{ version.content_hash.substring(0, 8) }}</code>
                </TableCell>
                <TableCell>
                  <span class="text-sm">{{ version.deployed_by_email || '-' }}</span>
                </TableCell>
                <TableCell>
                  <span class="text-sm">{{ new Date(version.deployed_at).toLocaleString() }}</span>
                </TableCell>
                <TableCell>{{ version.execution_count }}</TableCell>
                <TableCell>
                  <span class="text-sm">{{ version.notes || '-' }}</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  </section>
</template>
