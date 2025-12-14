<script setup lang="ts">
/**
 * Collections View
 *
 * List and manage data collections.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, computed, h, watch } from "vue";
import { useToast } from "vue-toastification";
import { useRoute } from "vue-router";
import { useUrlSearchParams } from "@vueuse/core";
import { useForm } from "vee-validate";
import { useCollectionsStore } from "../stores/collections";
import { useAuthStore } from "../stores/auth";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import FormField from "../components/FormField.vue";
import DataTable from "../components/DataTable.vue";

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
    // JSON validation should catch this, but handle just in case
    toast.error("Invalid schema JSON");
  }
});

// Watch for action=create in URL
watch(
  action,
  (newAction) => {
    if (newAction === "create" && authStore.isAdmin) {
      showCreateModal.value = true;
      // Clear the action param after opening modal
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
        h("router-link", { to: `/collections/${value}` }, value),
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
        h("small", { class: "text-muted" }, [
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
          variant: "contrast" as const,
        },
      ],
    });
  }

  return columns;
});
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>Collections</h1>
        <p>Manage your data collections</p>
      </hgroup>
    </header>

    <!-- Loading State -->
    <article v-if="collectionsStore.loading" aria-busy="true">
      Loading collections...
    </article>

    <!-- Empty State -->
    <article v-else-if="collectionsStore.collections.length === 0">
      <div data-empty data-empty-icon="📁">
        <p>No collections yet</p>
        <p>
          <small class="text-muted"
            >Create your first collection to start storing data.</small
          >
        </p>
        <button
          v-if="authStore.isAdmin"
          class="mt-2"
          @click="showCreateModal = true"
        >
          Create Collection
        </button>
      </div>
    </article>

    <!-- Collections Table -->
    <article v-else>
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
                variant: 'primary',
              }
            : undefined
        "
      />
    </article>

    <!-- Create Collection Modal -->
    <Modal v-model:open="showCreateModal" title="Create Collection">
      <form id="collection-form" @submit="onSubmit">
        <FormField
          name="name"
          type="text"
          label="Name (snake_case)"
          placeholder="my_collection"
        />

        <FormField
          name="label"
          type="text"
          label="Label"
          placeholder="My Collection"
        />

        <FormField
          name="schemaText"
          as="textarea"
          label="Schema (JSON)"
          :rows="10"
          style="font-family: monospace; font-size: 0.875rem"
        />
      </form>
      <template #footer>
        <button
          type="button"
          class="secondary"
          @click="showCreateModal = false"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="collection-form"
          :aria-busy="collectionsStore.loading"
          :disabled="collectionsStore.loading"
        >
          {{ collectionsStore.loading ? "" : "Create Collection" }}
        </button>
      </template>
    </Modal>
  </section>
</template>

<style scoped>
/* Page header layout */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header hgroup {
  margin: 0;
}

.page-header hgroup h1 {
  margin-bottom: var(--tb-spacing-xs);
}

.page-header hgroup p {
  margin: 0;
  color: var(--pico-muted-color);
}
</style>
