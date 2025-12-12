<script setup lang="ts">
/**
 * Collections View
 *
 * List and manage data collections.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useForm } from "vee-validate";
import { useCollectionsStore } from "../stores/collections";
import { useAuthStore } from "../stores/auth";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import FormField from "../components/FormField.vue";

const route = useRoute();
const collectionsStore = useCollectionsStore();
const authStore = useAuthStore();

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
    await collectionsStore.createCollection({
      name: values.name,
      label: values.label,
      schema,
    });
    showCreateModal.value = false;
    resetForm({
      values: {
        name: "",
        label: "",
        schemaText: defaultSchemaText,
      },
    });
  } catch (err) {
    // JSON validation should catch this, but handle just in case
    collectionsStore.error = "Invalid schema JSON";
  }
});

onMounted(async () => {
  await collectionsStore.fetchCollections();
  if (route.query.action === "create" && authStore.isAdmin) {
    showCreateModal.value = true;
  }
});

async function handleDelete(name: string) {
  if (
    confirm(
      `Are you sure you want to delete collection "${name}"? This will delete all records.`
    )
  ) {
    await collectionsStore.deleteCollection(name);
  }
}
</script>

<template>
  <div data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>Collections</h1>
        <p>Manage your data collections</p>
      </hgroup>
      <button v-if="authStore.isAdmin" @click="showCreateModal = true">
        + New Collection
      </button>
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
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Label</th>
            <th>Fields</th>
            <th>Created</th>
            <th v-if="authStore.isAdmin">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="collection in collectionsStore.collections"
            :key="collection.id"
          >
            <td>
              <router-link :to="`/collections/${collection.name}`">
                {{ collection.name }}
              </router-link>
            </td>
            <td>{{ collection.label }}</td>
            <td>{{ collection.schema?.fields?.length || 0 }} fields</td>
            <td>
              <small class="text-muted">{{
                new Date(collection.created_at).toLocaleDateString()
              }}</small>
            </td>
            <td v-if="authStore.isAdmin">
              <button
                class="small contrast"
                @click="handleDelete(collection.name)"
              >
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
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

        <small v-if="collectionsStore.error" class="text-error">
          {{ collectionsStore.error }}
        </small>
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
  </div>
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
