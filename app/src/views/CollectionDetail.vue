<script setup lang="ts">
/**
 * Collection Detail View
 *
 * View and manage records in a collection.
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, computed } from "vue";
import { useRoute } from "vue-router";
import { useCollectionsStore, type Record } from "../stores/collections";
import { useAuthStore } from "../stores/auth";
import Modal from "../components/Modal.vue";

const route = useRoute();
const collectionsStore = useCollectionsStore();
const authStore = useAuthStore();

const collectionName = computed(() => route.params.name as string);
const records = ref<Record[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;

const showCreateModal = ref(false);
const newRecordData = ref("{}");

onMounted(async () => {
  await collectionsStore.fetchCollection(collectionName.value);
  await loadRecords();
});

async function loadRecords() {
  const result = await collectionsStore.fetchRecords(
    collectionName.value,
    pageSize,
    (page.value - 1) * pageSize
  );
  records.value = result.records;
  total.value = result.total;
}

async function handleCreateRecord() {
  try {
    const data = JSON.parse(newRecordData.value);
    await collectionsStore.createRecord(collectionName.value, data);
    showCreateModal.value = false;
    newRecordData.value = "{}";
    await loadRecords();
  } catch (err) {
    alert("Invalid JSON data");
  }
}

async function handleDeleteRecord(recordId: string) {
  if (confirm("Are you sure you want to delete this record?")) {
    await collectionsStore.deleteRecord(collectionName.value, recordId);
    await loadRecords();
  }
}

function getFieldNames() {
  return (
    collectionsStore.currentCollection?.schema?.fields?.map((f) => f.name) || []
  );
}
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>
          {{ collectionsStore.currentCollection?.label || collectionName }}
        </h1>
        <p>
          Collection: <code>{{ collectionName }}</code>
        </p>
      </hgroup>
      <button @click="showCreateModal = true">+ New Record</button>
    </header>

    <!-- Schema Info -->
    <article class="schema-card">
      <header>
        <h3>Schema</h3>
      </header>
      <div v-if="collectionsStore.currentCollection" class="schema-fields">
        <mark
          v-for="field in collectionsStore.currentCollection.schema?.fields ||
          []"
          :key="field.name"
          data-status="neutral"
        >
          {{ field.name }}
          <small class="text-muted">({{ field.type }})</small>
          <small v-if="field.required" class="text-warning">*</small>
        </mark>
      </div>
    </article>

    <!-- Records Table -->
    <article>
      <header>
        <h3>Records ({{ total }})</h3>
      </header>

      <!-- Loading State -->
      <div v-if="collectionsStore.loading" aria-busy="true">
        Loading records...
      </div>

      <!-- Empty State -->
      <div v-else-if="records.length === 0" data-empty data-empty-icon="📄">
        <p>No records yet</p>
        <button class="small mt-2" @click="showCreateModal = true">
          Create Record
        </button>
      </div>

      <!-- Records Table -->
      <div v-else class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th v-for="field in getFieldNames().slice(0, 5)" :key="field">
                {{ field }}
              </th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in records" :key="record.id">
              <td>
                <code class="text-muted">{{ record.id.slice(0, 8) }}...</code>
              </td>
              <td v-for="field in getFieldNames().slice(0, 5)" :key="field">
                {{
                  typeof record.data[field] === "object"
                    ? JSON.stringify(record.data[field])
                    : record.data[field]
                }}
              </td>
              <td>
                <small class="text-muted">{{
                  new Date(record.created_at).toLocaleDateString()
                }}</small>
              </td>
              <td>
                <button
                  class="small contrast"
                  @click="handleDeleteRecord(record.id)"
                  :disabled="
                    !authStore.isAdmin && record.owner_id !== authStore.user?.id
                  "
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <footer v-if="total > pageSize">
        <button
          class="small secondary"
          :disabled="page === 1"
          @click="
            page--;
            loadRecords();
          "
        >
          Previous
        </button>
        <small class="text-muted">
          Page {{ page }} of {{ Math.ceil(total / pageSize) }}
        </small>
        <button
          class="small secondary"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="
            page++;
            loadRecords();
          "
        >
          Next
        </button>
      </footer>
    </article>

    <!-- Create Record Modal -->
    <Modal v-model:open="showCreateModal" title="Create Record">
      <form id="record-form" @submit.prevent="handleCreateRecord">
        <label for="data">
          Record Data (JSON)
          <textarea
            id="data"
            v-model="newRecordData"
            rows="10"
            style="font-family: monospace; font-size: 0.875rem"
            required
          ></textarea>
          <small class="text-muted">
            Fields: {{ getFieldNames().join(", ") }}
          </small>
        </label>

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
          form="record-form"
          :aria-busy="collectionsStore.loading"
          :disabled="collectionsStore.loading"
        >
          {{ collectionsStore.loading ? "" : "Create Record" }}
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

/* Schema card */
.schema-card {
  margin-bottom: var(--tb-spacing-lg);
}

.schema-fields {
  display: flex;
  flex-wrap: wrap;
  gap: var(--tb-spacing-sm);
}

.schema-fields mark {
  display: inline-flex;
  align-items: center;
  gap: var(--tb-spacing-xs);
}

/* Table wrapper for horizontal scroll */
.table-wrapper {
  overflow-x: auto;
}

/* Pagination footer */
article > footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--tb-spacing-md);
  padding-top: var(--tb-spacing-md);
  border-top: 1px solid var(--tb-border);
}
</style>
