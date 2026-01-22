<script setup lang="ts">
/**
 * Record Detail View
 *
 * View, edit, and delete a single record in a collection.
 */
import { onMounted, ref, computed } from 'vue';
import { useToast } from '../composables/useToast';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import { useCollectionsStore } from '../stores/collections';
import { useAuthStore } from '../stores/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Trash2, Save, Edit2 } from 'lucide-vue-next';

const toast = useToast();
const route = useRoute();
const router = useRouter();
const collectionsStore = useCollectionsStore();
const authStore = useAuthStore();

const collectionName = computed(() => route.params.name as string);
const recordId = computed(() => route.params.id as string);

const record = ref<any>(null);
const editData = ref('{}');
const showDeleteDialog = ref(false);
const showEditModal = ref(false);

onMounted(async () => {
  await loadRecord();
  await collectionsStore.fetchCollection(collectionName.value);
});

async function loadRecord() {
  const result = await collectionsStore.fetchRecord(collectionName.value, recordId.value);
  if (result) {
    record.value = result;
    editData.value = JSON.stringify(result.data, null, 2);
  } else {
    toast.error(collectionsStore.error || 'Failed to load record');
    router.push({ name: 'collection-detail', params: { name: collectionName.value } });
  }
}

async function handleUpdate() {
  try {
    const data = JSON.parse(editData.value);
    const result = await collectionsStore.updateRecord(collectionName.value, recordId.value, data);
    if (result) {
      toast.success('Record updated successfully');
      showEditModal.value = false;
      await loadRecord();
    } else {
      toast.error(collectionsStore.error || 'Failed to update record');
    }
  } catch {
    toast.error('Invalid JSON data');
  }
}

async function handleDelete() {
  const result = await collectionsStore.deleteRecord(collectionName.value, recordId.value);
  if (result) {
    toast.success('Record deleted successfully');
    router.push({ name: 'collection-detail', params: { name: collectionName.value } });
  } else {
    toast.error(collectionsStore.error || 'Failed to delete record');
  }
}

function getFieldValue(fieldName: string): any {
  return record.value?.data?.[fieldName] ?? null;
}

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

const canEdit = computed(() => {
  if (!authStore.isAdmin) {
    return false;
  }
  // Check if user owns the record or is admin
  if (record.value?.owner_id && record.value.owner_id !== authStore.user?.id) {
    return authStore.isAdmin;
  }
  return true;
});

const canDelete = computed(() => {
  if (!authStore.isAdmin) {
    return false;
  }
  // Check if user owns the record or is admin
  if (record.value?.owner_id && record.value.owner_id !== authStore.user?.id) {
    return authStore.isAdmin;
  }
  return true;
});
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <div class="flex items-center gap-4">
        <RouterLink
          :to="{ name: 'collection-detail', params: { name: collectionName } }"
          class="text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft class="h-5 w-5" />
        </RouterLink>
        <div>
          <h1 class="text-3xl font-bold tracking-tight">Record Details</h1>
          <p class="text-muted-foreground">
            Collection: <code class="text-sm">{{ collectionName }}</code>
          </p>
        </div>
      </div>
    </header>

    <!-- Loading State -->
    <Card v-if="collectionsStore.loading && !record">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading record...</p>
      </CardContent>
    </Card>

    <!-- Record Not Found -->
    <Card v-else-if="!record">
      <CardContent class="flex flex-col items-center justify-center py-10">
        <p class="text-sm text-muted-foreground mb-4">Record not found</p>
        <Button
          variant="outline"
          @click="router.push({ name: 'collection-detail', params: { name: collectionName } })"
        >
          Back to Collection
        </Button>
      </CardContent>
    </Card>

    <!-- Record Details -->
    <template v-else>
      <!-- Metadata Card -->
      <Card>
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle>Metadata</CardTitle>
            <div v-if="authStore.isAdmin" class="flex gap-2">
              <Button v-if="canEdit" variant="outline" size="sm" @click="showEditModal = true">
                <Edit2 class="h-4 w-4 mr-2" />
                Edit
              </Button>
              <Button
                v-if="canDelete"
                variant="destructive"
                size="sm"
                @click="showDeleteDialog = true"
              >
                <Trash2 class="h-4 w-4 mr-2" />
                Delete
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <Label class="text-sm font-medium text-muted-foreground">Record ID</Label>
              <p class="mt-1">
                <code class="text-sm">{{ record.id }}</code>
              </p>
            </div>
            <div v-if="record.owner_id">
              <Label class="text-sm font-medium text-muted-foreground">Owner ID</Label>
              <p class="mt-1">
                <code class="text-sm">{{ record.owner_id }}</code>
              </p>
            </div>
            <div>
              <Label class="text-sm font-medium text-muted-foreground">Created</Label>
              <p class="mt-1 text-sm">
                {{ new Date(record.created_at).toLocaleString() }}
              </p>
            </div>
            <div>
              <Label class="text-sm font-medium text-muted-foreground">Updated</Label>
              <p class="mt-1 text-sm">
                {{ new Date(record.updated_at).toLocaleString() }}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Data Card -->
      <Card>
        <CardHeader>
          <CardTitle>Data</CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="collectionsStore.currentCollection" class="space-y-4">
            <div
              v-for="field in (collectionsStore.currentCollection.schema?.fields as any[]) || []"
              :key="(field as any).name"
              class="space-y-2"
            >
              <div class="flex items-center gap-2">
                <Label class="text-sm font-medium">{{ (field as any).name }}</Label>
                <Badge variant="outline" class="text-xs">
                  {{ (field as any).type }}
                </Badge>
                <Badge v-if="(field as any).required" variant="secondary" class="text-xs">
                  Required
                </Badge>
              </div>
              <div class="rounded-md border bg-muted/50 p-3">
                <pre
                  v-if="typeof getFieldValue(field.name) === 'object'"
                  class="text-sm font-mono whitespace-pre-wrap break-words"
                  >{{ formatValue(getFieldValue(field.name)) }}
                </pre>
                <p v-else class="text-sm">
                  {{ formatValue(getFieldValue(field.name)) }}
                </p>
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-muted-foreground">Loading schema...</div>
        </CardContent>
      </Card>

      <!-- Raw JSON Card -->
      <Card>
        <CardHeader>
          <CardTitle>Raw JSON</CardTitle>
        </CardHeader>
        <CardContent>
          <pre class="rounded-md border bg-muted/50 p-4 text-sm font-mono overflow-auto"
            >{{ JSON.stringify(record.data, null, 2) }}
          </pre>
        </CardContent>
      </Card>
    </template>

    <!-- Edit Modal -->
    <Dialog v-model:open="showEditModal">
      <DialogContent class="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Record</DialogTitle>
          <DialogDescription>
            Update the record data. The data will be validated against the collection schema.
          </DialogDescription>
        </DialogHeader>

        <form id="edit-form" class="space-y-4" @submit.prevent="handleUpdate">
          <div class="space-y-2">
            <Label for="data">Record Data (JSON)</Label>
            <Textarea id="data" v-model="editData" :rows="15" class="font-mono text-sm" required />
            <p class="text-xs text-muted-foreground">
              Fields:
              {{
                Array.isArray(collectionsStore.currentCollection?.schema?.fields)
                  ? (collectionsStore.currentCollection.schema.fields as any[])
                      .map((f: any) => f.name)
                      .join(', ')
                  : 'N/A'
              }}
            </p>
          </div>
        </form>

        <DialogFooter>
          <Button type="button" variant="ghost" @click="showEditModal = false"> Cancel </Button>
          <Button type="submit" form="edit-form" :disabled="collectionsStore.loading">
            <Save class="h-4 w-4 mr-2" />
            {{ collectionsStore.loading ? 'Updating...' : 'Update Record' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Delete Confirmation Dialog -->
    <Dialog v-model:open="showDeleteDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Record</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this record? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="ghost" @click="showDeleteDialog = false"> Cancel </Button>
          <Button type="button" variant="destructive" @click="handleDelete">
            <Trash2 class="h-4 w-4 mr-2" />
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
