<script setup lang="ts">
/**
 * Collections View
 *
 * List and manage data collections.
 */
import { onMounted, computed, h } from 'vue';
import { RouterLink } from 'vue-router';
import { useToast } from '../composables/useToast';
import { useModal } from '../composables/useModal';
import { useField, useForm } from 'vee-validate';
import { useCollectionsStore } from '../stores/collections';
import { useAuthStore } from '../stores/auth';
import { validationSchemas } from '../composables/useFormValidation';
import DataTable from '../components/DataTable.vue';
import SchemaEditor from '../components/SchemaEditor.vue';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { FolderOpen } from 'lucide-vue-next';

const toast = useToast();
const collectionsStore = useCollectionsStore();
const authStore = useAuthStore();

// Modal state with URL param support (opens on ?action=create)
const { isOpen: showCreateModal, open: openCreateModal, close: closeCreateModal } = useModal();

const defaultSchemaText =
  '{\n  "fields": [\n    {\n      "name": "title",\n      "type": "string",\n      "required": true\n    }\n  ]\n}';

const { handleSubmit, resetForm } = useForm({
  validationSchema: validationSchemas.createCollection,
  initialValues: {
    name: '',
    label: '',
    schemaText: defaultSchemaText,
    readOnly: false,
  },
});

const nameField = useField('name');
const labelField = useField('label');
const schemaTextField = useField('schemaText');
const readOnlyField = useField('readOnly');

const onSubmit = handleSubmit(async (values) => {
  try {
    const schema = JSON.parse(values.schemaText);

    // Add access control metadata to schema if read-only is enabled
    if (values.readOnly) {
      schema.access = {
        read: ['admin', 'user'],
        create: ['admin'],
        update: ['admin'],
        delete: ['admin'],
      };
    }

    const result = await collectionsStore.createCollection({
      name: values.name,
      label: values.label,
      schema,
    });
    if (result) {
      toast.success(`Collection "${values.name}" created successfully`);
      closeCreateModal();
      resetForm({
        values: {
          name: '',
          label: '',
          schemaText: defaultSchemaText,
          readOnly: false,
        },
      });
    } else {
      toast.error(collectionsStore.error || 'Failed to create collection');
    }
  } catch (err) {
    toast.error('Invalid schema JSON');
  }
});

onMounted(async () => {
  await collectionsStore.fetchCollections();
});

async function handleDelete(name: string) {
  if (
    confirm(`Are you sure you want to delete collection "${name}"? This will delete all records.`)
  ) {
    const result = await collectionsStore.deleteCollection(name);
    if (result) {
      toast.success(`Collection "${name}" deleted successfully`);
    } else {
      toast.error(collectionsStore.error || 'Failed to delete collection');
    }
  }
}

const collectionColumns = computed(() => {
  const columns: any[] = [
    {
      key: 'name',
      label: 'Name',
      render: (value: any) =>
        h(
          RouterLink,
          {
            to: { name: 'collection-detail', params: { name: value } },
            class: 'text-primary hover:underline font-medium cursor-pointer transition-colors',
          },
          () => value
        ),
    },
    { key: 'label', label: 'Label' },
    {
      key: 'fields',
      label: 'Fields',
      render: (_value: any, row: any) => `${row.schema?.fields?.length || 0} fields`,
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (value: any) =>
        h('span', { class: 'text-sm text-muted-foreground' }, [
          new Date(value).toLocaleDateString(),
        ]),
    },
  ];

  if (authStore.isAdmin) {
    columns.push({
      key: 'actions',
      label: 'Actions',
      actions: [
        {
          label: 'Delete',
          action: (row: any) => handleDelete(row.name),
          variant: 'destructive' as const,
        },
      ],
    });
  }

  return columns;
});
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Collections</h1>
      <p class="text-muted-foreground">Manage your data collections</p>
    </header>

    <!-- Loading State -->
    <Card v-if="collectionsStore.loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading collections...</p>
      </CardContent>
    </Card>

    <!-- Empty State -->
    <Empty v-else-if="collectionsStore.collections.length === 0">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <FolderOpen />
        </EmptyMedia>
        <EmptyTitle>No collections yet</EmptyTitle>
        <EmptyDescription> Create your first collection to start storing data. </EmptyDescription>
      </EmptyHeader>
      <EmptyContent v-if="authStore.isAdmin">
        <Button @click="openCreateModal"> Create Collection </Button>
      </EmptyContent>
    </Empty>

    <!-- Collections Table -->
    <Card v-else>
      <DataTable
        :data="collectionsStore.collections"
        :columns="collectionColumns"
        :page-size="20"
        search-placeholder="Search collections..."
        :header-action="
          authStore.isAdmin
            ? {
                label: 'New Collection',
                action: openCreateModal,
                variant: 'default',
                icon: 'Plus',
              }
            : undefined
        "
      />
    </Card>

    <!-- Create Collection Modal -->
    <Dialog v-model:open="showCreateModal">
      <DialogContent class="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Collection</DialogTitle>
          <DialogDescription>
            Create a new data collection with custom fields and schema.
          </DialogDescription>
        </DialogHeader>

        <form id="collection-form" class="space-y-4" @submit.prevent="onSubmit">
          <div class="space-y-2">
            <Label for="name">Name (snake_case)</Label>
            <Input
              id="name"
              v-model="nameField.value.value"
              placeholder="my_collection"
              :aria-invalid="nameField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="nameField.errorMessage.value" class="text-sm text-destructive">
              {{ nameField.errorMessage.value }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="label">Label</Label>
            <Input
              id="label"
              v-model="labelField.value.value"
              placeholder="My Collection"
              :aria-invalid="labelField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="labelField.errorMessage.value" class="text-sm text-destructive">
              {{ labelField.errorMessage.value }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="schema">Schema</Label>
            <SchemaEditor v-model="schemaTextField.value.value" />
            <p v-if="schemaTextField.errorMessage.value" class="text-sm text-destructive">
              {{ schemaTextField.errorMessage.value }}
            </p>
          </div>

          <Separator />

          <div class="space-y-3">
            <Label class="text-base">Access Control</Label>
            <div class="flex items-start space-x-3">
              <Checkbox
                id="read-only"
                :model-value="readOnlyField.value.value"
                @update:model-value="readOnlyField.value.value = $event"
              />
              <div class="space-y-1 leading-none">
                <Label for="read-only" class="text-sm font-normal cursor-pointer">
                  Read-only for non-admins
                </Label>
                <p class="text-xs text-muted-foreground">
                  Non-admin users can view records but cannot create, update, or delete them.
                </p>
              </div>
            </div>
          </div>
        </form>

        <DialogFooter>
          <Button type="button" variant="ghost" @click="closeCreateModal"> Cancel </Button>
          <Button type="submit" form="collection-form" :disabled="collectionsStore.loading">
            {{ collectionsStore.loading ? 'Creating...' : 'Create Collection' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
