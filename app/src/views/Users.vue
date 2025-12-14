<script setup lang="ts">
/**
 * Users View
 *
 * Manage user accounts (admin only).
 * Uses semantic HTML elements following PicoCSS conventions.
 */
import { onMounted, ref, computed, h, watch } from "vue";
import { useToast } from "vue-toastification";
import { useRoute } from "vue-router";
import { useUrlSearchParams } from "@vueuse/core";
import { useForm, Field } from "vee-validate";
import { useUsersStore } from "../stores/users";
import { validationSchemas } from "../composables/useFormValidation";
import Modal from "../components/Modal.vue";
import FormField from "../components/FormField.vue";
import DataTable from "../components/DataTable.vue";

const toast = useToast();
const route = useRoute();
const usersStore = useUsersStore();

// URL search params for action=create
const params = useUrlSearchParams("history");
const action = computed(() => params.action as string | null);

const showCreateModal = ref(false);

const { handleSubmit, resetForm } = useForm({
  validationSchema: validationSchemas.createUser,
  initialValues: {
    email: "",
    password: "",
    is_admin: false,
  },
});

const onSubmit = handleSubmit(async (values) => {
  const result = await usersStore.createUser(values);
  if (result) {
    toast.success(`User "${values.email}" created successfully`);
    showCreateModal.value = false;
    resetForm();
  } else {
    toast.error(usersStore.error || "Failed to create user");
  }
});

// Watch for action=create in URL
watch(
  action,
  (newAction) => {
    if (newAction === "create") {
      showCreateModal.value = true;
      // Clear the action param after opening modal
      params.action = undefined;
    }
  },
  { immediate: true }
);

onMounted(async () => {
  await usersStore.fetchUsers();
});

async function handleToggleAdmin(userId: string, currentStatus: boolean) {
  const result = await usersStore.updateUser(userId, {
    is_admin: !currentStatus,
  });
  if (result) {
    toast.success(
      `User ${!currentStatus ? "promoted to admin" : "removed from admin"}`
    );
  } else {
    toast.error(usersStore.error || "Failed to update user");
  }
}

async function handleDelete(userId: string) {
  if (confirm("Are you sure you want to delete this user?")) {
    const result = await usersStore.deleteUser(userId);
    if (result) {
      toast.success("User deleted successfully");
    } else {
      toast.error(usersStore.error || "Failed to delete user");
    }
  }
}

const userColumns = computed(() => [
  { key: "email", label: "Email" },
  {
    key: "role",
    label: "Role",
    render: (_value: any, row: any) => {
      return h(
        "mark",
        { "data-status": row.is_admin ? "info" : "neutral" },
        row.is_admin ? "Admin" : "User"
      );
    },
  },
  {
    key: "created_at",
    label: "Created",
    render: (value: any) => {
      return h("small", { class: "text-muted" }, [
        new Date(value).toLocaleDateString(),
      ]);
    },
  },
  {
    key: "actions",
    label: "Actions",
    actions: [
      {
        label: (row: any) => (row.is_admin ? "Remove Admin" : "Make Admin"),
        action: (row: any) => handleToggleAdmin(row.id, row.is_admin),
        variant: "secondary" as const,
      },
      {
        label: "Delete",
        action: (row: any) => handleDelete(row.id),
        variant: "contrast" as const,
      },
    ],
  },
]);
</script>

<template>
  <section data-animate="fade-in">
    <header class="page-header">
      <hgroup>
        <h1>Users</h1>
        <p>Manage user accounts</p>
      </hgroup>
    </header>

    <!-- Loading State -->
    <article v-if="usersStore.loading" aria-busy="true">
      Loading users...
    </article>

    <!-- Users Table -->
    <article v-else>
      <DataTable
        :data="usersStore.users"
        :columns="userColumns as any"
        :page-size="20"
        search-placeholder="Search users..."
        :header-action="{
          label: '+ New User',
          action: () => {
            showCreateModal = true;
          },
          variant: 'primary',
        }"
      />
    </article>

    <!-- Create User Modal -->
    <Modal v-model:open="showCreateModal" title="Create User">
      <form id="user-form" @submit="onSubmit">
        <FormField name="email" type="email" label="Email" />

        <FormField
          name="password"
          type="password"
          label="Password"
          helper="Password must be at least 8 characters"
        />

        <Field name="is_admin" v-slot="{ field }">
          <label>
            <input v-bind="field" type="checkbox" role="switch" />
            Admin privileges
          </label>
        </Field>
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
          form="user-form"
          :aria-busy="usersStore.loading"
          :disabled="usersStore.loading"
        >
          {{ usersStore.loading ? "" : "Create User" }}
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
