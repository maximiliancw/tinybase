<script setup lang="ts">
/**
 * Collection Detail View
 *
 * View and manage records in a collection.
 */
import { onMounted, ref, computed, h } from 'vue';
import { useToast } from '../composables/useToast';
import { useRoute } from 'vue-router';
import { useInfiniteScroll } from '@vueuse/core';
import { useCollectionsStore, type Record } from '../stores/collections';
import { useAuthStore } from '../stores/auth';
import DataTable from '../components/DataTable.vue';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { FileText, Database, Calendar, Hash } from 'lucide-vue-next';

const toast = useToast();
const route = useRoute();
const collectionsStore = useCollectionsStore();
const authStore = useAuthStore();

const collectionName = computed(() => route.params.name as string);
const records = ref<Record[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loadingMore = ref(false);

const showCreateModal = ref(false);
const newRecordData = ref('{}');

const scrollContainer = ref<HTMLElement>();

onMounted(async () => {
  await collectionsStore.fetchCollection(collectionName.value);
  await loadRecords(true); // Reset on initial load
});

async function loadRecords(reset = false) {
  loadingMore.value = true;
  try {
    const result = await collectionsStore.fetchRecords(
      collectionName.value,
      pageSize,
      (page.value - 1) * pageSize
    );
    if (reset) {
      records.value = result.records;
    } else {
      records.value = [...records.value, ...result.records];
    }
    total.value = result.total;
  } finally {
    loadingMore.value = false;
  }
}

async function loadMore() {
  if (loadingMore.value || page.value * pageSize >= total.value) {
    return;
  }
  page.value++;
  await loadRecords(false); // Don't reset, append
}

// Infinite scroll
useInfiniteScroll(
  scrollContainer,
  () => {
    loadMore();
  },
  { distance: 10 }
);

async function handleCreateRecord() {
  try {
    const data = JSON.parse(newRecordData.value);
    const result = await collectionsStore.createRecord(collectionName.value, data);
    if (result) {
      toast.success('Record created successfully');
      showCreateModal.value = false;
      newRecordData.value = '{}';
      await loadRecords(true);
    } else {
      toast.error(collectionsStore.error || 'Failed to create record');
    }
  } catch (err) {
    toast.error('Invalid JSON data');
  }
}

async function handleDeleteRecord(recordId: string) {
  if (confirm('Are you sure you want to delete this record?')) {
    const result = await collectionsStore.deleteRecord(collectionName.value, recordId);
    if (result) {
      toast.success('Record deleted successfully');
      await loadRecords(true);
    } else {
      toast.error(collectionsStore.error || 'Failed to delete record');
    }
  }
}

function getFieldNames() {
  return collectionsStore.currentCollection?.schema?.fields?.map((f) => f.name) || [];
}

const recordColumns = computed(() => {
  const fieldNames = getFieldNames().slice(0, 5);
  const columns: any[] = [
    {
      key: 'id',
      label: 'ID',
      render: (value: any) =>
        h('code', { class: 'text-xs text-muted-foreground' }, `${value.slice(0, 8)}...`),
    },
  ];

  // Add dynamic field columns
  fieldNames.forEach((field) => {
    columns.push({
      key: field,
      label: field,
      render: (_value: any, row: any) => {
        const fieldValue = row.data[field];
        if (typeof fieldValue === 'object') {
          return JSON.stringify(fieldValue);
        }
        return fieldValue ?? '-';
      },
    });
  });

  columns.push({
    key: 'created_at',
    label: 'Created',
    render: (value: any) =>
      h('span', { class: 'text-sm text-muted-foreground' }, [new Date(value).toLocaleDateString()]),
  });

  columns.push({
    key: 'actions',
    label: 'Actions',
    actions: [
      {
        label: 'Delete',
        action: (row: any) => handleDeleteRecord(row.id),
        variant: 'destructive' as const,
        disabled: (row: any) => !authStore.isAdmin && row.owner_id !== authStore.user?.id,
      },
    ],
  });

  return columns;
});
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <div class="flex items-center gap-3">
        <h1 class="text-3xl font-bold tracking-tight">
          {{ collectionsStore.currentCollection?.label || collectionName }}
        </h1>
      </div>
      <p class="text-muted-foreground">
        Collection: <code class="text-sm">{{ collectionName }}</code>
      </p>
    </header>

    <!-- Stats Cards -->
    <div class="grid gap-4 md:grid-cols-3">
      <Card>
        <CardContent class="pt-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-muted-foreground">Total Records</p>
              <p class="text-2xl font-bold">{{ total.toLocaleString() }}</p>
            </div>
            <div class="rounded-full bg-primary/10 p-3">
              <Database class="h-5 w-5 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="pt-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-muted-foreground">Fields</p>
              <p class="text-2xl font-bold">
                {{ collectionsStore.currentCollection?.schema?.fields?.length || 0 }}
              </p>
            </div>
            <div class="rounded-full bg-primary/10 p-3">
              <Hash class="h-5 w-5 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent class="pt-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-muted-foreground">Created</p>
              <p class="text-sm font-semibold">
                {{
                  collectionsStore.currentCollection?.created_at
                    ? new Date(collectionsStore.currentCollection.created_at).toLocaleDateString()
                    : '-'
                }}
              </p>
            </div>
            <div class="rounded-full bg-primary/10 p-3">
              <Calendar class="h-5 w-5 text-primary" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Schema Info -->
    <Card>
      <CardHeader>
        <CardTitle>Schema</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="collectionsStore.currentCollection" class="flex flex-wrap gap-2">
          <Badge
            v-for="field in collectionsStore.currentCollection.schema?.fields || []"
            :key="field.name"
            variant="outline"
            class="gap-1"
          >
            {{ field.name }}
            <span class="text-xs text-muted-foreground">({{ field.type }})</span>
            <span v-if="field.required" class="text-yellow-500">*</span>
          </Badge>
        </div>
      </CardContent>
    </Card>

    <!-- Records Table -->
    <Card>
      <CardHeader>
        <CardTitle>Records ({{ total }})</CardTitle>
      </CardHeader>
      <CardContent>
        <!-- Loading State -->
        <div v-if="collectionsStore.loading" class="flex items-center justify-center py-10">
          <p class="text-sm text-muted-foreground">Loading records...</p>
        </div>

        <!-- Empty State -->
        <Empty v-else-if="records.length === 0">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileText />
            </EmptyMedia>
            <EmptyTitle>No records yet</EmptyTitle>
            <EmptyDescription>
              Create your first record to get started with this collection.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button size="sm" @click="showCreateModal = true"> Create Record </Button>
          </EmptyContent>
        </Empty>

        <!-- Records Table -->
        <div v-else ref="scrollContainer">
          <DataTable
            :data="records"
            :columns="recordColumns"
            :paginated="false"
            search-placeholder="Search records..."
            :header-action="{
              label: '+ New Record',
              action: () => {
                showCreateModal = true;
              },
              variant: 'default',
              icon: 'Plus',
            }"
          />

          <!-- Server-side Pagination -->
          <div v-if="total > pageSize" class="flex items-center justify-between border-t pt-4 mt-4">
            <Button
              size="sm"
              variant="ghost"
              :disabled="page === 1"
              @click="
                page--;
                loadRecords(true);
              "
            >
              Previous
            </Button>
            <span class="text-sm text-muted-foreground">
              Page {{ page }} of {{ Math.ceil(total / pageSize) }} ({{ total }}
              total)
            </span>
            <Button
              size="sm"
              variant="ghost"
              :disabled="page >= Math.ceil(total / pageSize)"
              @click="
                page++;
                loadRecords(true);
              "
            >
              Next
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Create Record Modal -->
    <Dialog v-model:open="showCreateModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Record</DialogTitle>
        </DialogHeader>

        <form id="record-form" class="space-y-4" @submit.prevent="handleCreateRecord">
          <div class="space-y-2">
            <Label for="data">Record Data (JSON)</Label>
            <Textarea
              id="data"
              v-model="newRecordData"
              :rows="10"
              class="font-mono text-sm"
              required
            />
            <p class="text-xs text-muted-foreground">Fields: {{ getFieldNames().join(', ') }}</p>
          </div>
        </form>

        <DialogFooter>
          <Button type="button" variant="ghost" @click="showCreateModal = false"> Cancel </Button>
          <Button type="submit" form="record-form" :disabled="collectionsStore.loading">
            {{ collectionsStore.loading ? 'Creating...' : 'Create Record' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
