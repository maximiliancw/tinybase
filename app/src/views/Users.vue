<script setup lang="ts">
/**
 * Users View
 *
 * Manage user accounts (admin only).
 */
import { onMounted, ref, computed, h, watch } from "vue";
import { useToast } from "vue-toastification";
import { useRoute } from "vue-router";
import { useUrlSearchParams } from "@vueuse/core";
import { useForm, useField, Field } from "vee-validate";
import { useUsersStore } from "../stores/users";
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
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";

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

const emailField = useField("email");
const passwordField = useField("password");
const isAdminField = useField("is_admin");

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
        Badge,
        { variant: row.is_admin ? "default" : "secondary" },
        () => (row.is_admin ? "Admin" : "User")
      );
    },
  },
  {
    key: "created_at",
    label: "Created",
    render: (value: any) => {
      return h("span", { class: "text-sm text-muted-foreground" }, [
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
        variant: "destructive" as const,
      },
    ],
  },
]);
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Users</h1>
      <p class="text-muted-foreground">Manage user accounts</p>
    </header>

    <!-- Loading State -->
    <Card v-if="usersStore.loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading users...</p>
      </CardContent>
    </Card>

    <!-- Users Table -->
    <Card v-else>
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
          variant: 'default',
          icon: 'Plus',
        }"
      />
    </Card>

    <!-- Create User Modal -->
    <Dialog v-model:open="showCreateModal">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>

        <form id="user-form" @submit.prevent="onSubmit" class="space-y-4">
          <div class="space-y-2">
            <Label for="email">Email</Label>
            <Input
              id="email"
              v-model="emailField.value.value"
              type="email"
              :aria-invalid="emailField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="emailField.errorMessage.value" class="text-sm text-destructive">
              {{ emailField.errorMessage.value }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="password">Password</Label>
            <Input
              id="password"
              v-model="passwordField.value.value"
              type="password"
              :aria-invalid="passwordField.errorMessage.value ? 'true' : undefined"
            />
            <p class="text-xs text-muted-foreground">
              Password must be at least 8 characters
            </p>
            <p v-if="passwordField.errorMessage.value" class="text-sm text-destructive">
              {{ passwordField.errorMessage.value }}
            </p>
          </div>

          <div class="flex items-center space-x-2">
            <Switch
              id="is_admin"
              :checked="isAdminField.value.value"
              @update:checked="isAdminField.value.value = $event"
            />
            <Label for="is_admin" class="cursor-pointer">Admin privileges</Label>
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
            form="user-form"
            :disabled="usersStore.loading"
          >
            {{ usersStore.loading ? "Creating..." : "Create User" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </section>
</template>
