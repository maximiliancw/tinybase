<script setup lang="ts">
/**
 * Collections View
 *
 * List and manage data collections.
 */
import { onMounted, ref, computed, h, watch } from "vue";
import { useToast } from "../composables/useToast";
import { useRoute } from "vue-router";
import { useUrlSearchParams } from "@vueuse/core";
import { useField, useForm } from "vee-validate";
import { useCollectionsStore } from "../stores/collections";
import { useAuthStore } from "../stores/auth";
import { validationSchemas } from "../composables/useFormValidation";
import DataTable from "../components/DataTable.vue";
import { Card, CardContent } from "@/components/ui/card";
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

const toast = useToast();
const route = useRoute();
const collectionsStore = useCollectionsStore();
const authStore = useAuthStore();

// URL search params for action=create
const params = useUrlSearchParams("history");
const action = computed(() => params.action as string | null);

const showCreateModal = ref(false);
const defaultSchemaText =
  '{\n  "fields": [\n    {\n      "name": "title",\n      "type": "string",\n      "required": true\n    }\n  ]\n}';

const { handleSubmit, resetForm } = useForm({
  validationSchema: validationSchemas.createCollection,
  initialValues: {
    name: "",
    label: "",
    schemaText: defaultSchemaText,
  },
});

const nameField = useField("name");
const labelField = useField("label");
const schemaTextField = useField("schemaText");

const onSubmit = handleSubmit(async (values) => {
  try {
    const schema = JSON.parse(values.schemaText);
    const result = await collectionsStore.createCollection({
      name: values.name,
      label: values.label,
      schema,
    });
    if (result) {
      toast.success(`Collection "${values.name}" created successfully`);
      showCreateModal.value = false;
      resetForm({
        values: {
          name: "",
          label: "",
          schemaText: defaultSchemaText,
        },
      });
    } else {
      toast.error(collectionsStore.error || "Failed to create collection");
    }
  } catch (err) {
    toast.error("Invalid schema JSON");
  }
});

// Watch for action=create in URL
watch(
  action,
  (newAction) => {
    if (newAction === "create" && authStore.isAdmin) {
      showCreateModal.value = true;
      params.action = undefined;
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await collectionsStore.fetchCollections();
});

async function handleDelete(name: string) {
  if (
    confirm(
      `Are you sure you want to delete collection "${name}"? This will delete all records.`
    )
  ) {
    const result = await collectionsStore.deleteCollection(name);
    if (result) {
      toast.success(`Collection "${name}" deleted successfully`);
    } else {
      toast.error(collectionsStore.error || "Failed to delete collection");
    }
  }
}

const collectionColumns = computed(() => {
  const columns: any[] = [
    {
      key: "name",
      label: "Name",
      render: (value: any) =>
        h("router-link", { to: `/collections/${value}`, class: "text-primary hover:underline" }, value),
    },
    { key: "label", label: "Label" },
    {
      key: "fields",
      label: "Fields",
      render: (_value: any, row: any) =>
        `${row.schema?.fields?.length || 0} fields`,
    },
    {
      key: "created_at",
      label: "Created",
      render: (value: any) =>
        h("span", { class: "text-sm text-muted-foreground" }, [
          new Date(value).toLocaleDateString(),
        ]),
    },
  ];

  if (authStore.isAdmin) {
    columns.push({
      key: "actions",
      label: "Actions",
      actions: [
        {
          label: "Delete",
          action: (row: any) => handleDelete(row.name),
          variant: "destructive" as const,
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
    <Card v-else-if="collectionsStore.collections.length === 0">
      <CardContent class="flex flex-col items-center justify-center py-16 text-center">
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted text-3xl">
          📁
        </div>
        <h3 class="mb-1 text-lg font-semibold">No collections yet</h3>
        <p class="mb-4 text-sm text-muted-foreground">
          Create your first collection to start storing data.
        </p>
        <Button
          v-if="authStore.isAdmin"
          @click="showCreateModal = true"
        >
          Create Collection
        </Button>
      </CardContent>
    </Card>

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
                label: '+ New Collection',
                action: () => {
                  showCreateModal = true;
                },
                variant: 'default',
                icon: 'Plus',
              }
            : undefined
        "
      />
    </Card>

    <!-- Create Collection Modal -->
    <Dialog v-model:open="showCreateModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Collection</DialogTitle>
        </DialogHeader>

        <form id="collection-form" @submit.prevent="onSubmit" class="space-y-4">
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
            <Label for="schema">Schema (JSON)</Label>
            <Textarea
              id="schema"
              v-model="schemaTextField.value.value"
              :rows="10"
              class="font-mono text-sm"
              :aria-invalid="schemaTextField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="schemaTextField.errorMessage.value" class="text-sm text-destructive">
              {{ schemaTextField.errorMessage.value }}
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
            form="collection-form"
            :disabled="collectionsStore.loading"
          >
            {{ collectionsStore.loading ? "Creating..." : "Create Collection" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
