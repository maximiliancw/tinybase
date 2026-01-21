<script setup lang="ts">
/**
 * Profile View
 *
 * Manage user account settings and password.
 */
import { ref, computed, onMounted } from 'vue';
import { useToast } from '../composables/useToast';
import { useForm, useField } from 'vee-validate';
import { useAuthStore } from '../stores/auth';
import { api } from '@/api';
import { validationSchemas } from '../composables/useFormValidation';
import Icon from '../components/Icon.vue';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

const toast = useToast();
const authStore = useAuthStore();
const savingPassword = ref(false);
const loading = ref(true);

// Computed value for email to ensure reactivity
const userEmail = computed(() => authStore.user?.email || '');

onMounted(async () => {
  // Ensure user data is loaded
  if (!authStore.user && authStore.accessToken) {
    try {
      await authStore.fetchUser();
    } catch (err) {
      toast.error('Failed to load user data');
    }
  }
  loading.value = false;
});

// Password change form
const { handleSubmit: handlePasswordSubmit, resetForm: resetPasswordForm } = useForm({
  validationSchema: validationSchemas.changePassword,
  initialValues: {
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  },
});

const currentPasswordField = useField('currentPassword');
const newPasswordField = useField('newPassword');
const confirmPasswordField = useField('confirmPassword');

const onPasswordSubmit = handlePasswordSubmit(async (values) => {
  if (!authStore.user?.id) {
    toast.error('User not found');
    return;
  }

  // Verify current password by attempting to login
  const loginSuccess = await authStore.login(authStore.user.email, values.currentPassword);
  if (!loginSuccess) {
    toast.error('Current password is incorrect');
    return;
  }

  savingPassword.value = true;

  try {
    // Update password
    await api.admin.updateUser({
      path: { user_id: authStore.user.id },
      body: { password: values.newPassword },
    });

    toast.success('Password updated successfully');
    resetPasswordForm();
  } catch (err: any) {
    toast.error(err.error?.detail || 'Failed to update password');
  } finally {
    savingPassword.value = false;
  }
});

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
</script>

<template>
  <section class="space-y-6 animate-in fade-in duration-500">
    <!-- Page Header -->
    <header class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight">Account Settings</h1>
      <p class="text-muted-foreground">Manage your profile and account security</p>
    </header>

    <!-- Loading State -->
    <Card v-if="loading">
      <CardContent class="flex items-center justify-center py-10">
        <p class="text-sm text-muted-foreground">Loading account information...</p>
      </CardContent>
    </Card>

    <template v-else>
      <!-- Account Information -->
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>Your account details and status</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <Label>Email</Label>
            <div class="flex items-center gap-2">
              <Input :model-value="userEmail" readonly class="bg-muted" />
              <Badge v-if="authStore.isAdmin" variant="secondary"> Admin </Badge>
            </div>
            <p class="text-xs text-muted-foreground">
              Contact your administrator to change your email address
            </p>
          </div>

          <Separator />

          <div class="space-y-2">
            <Label>Account Created</Label>
            <p class="text-sm text-muted-foreground">
              {{ authStore.user?.created_at ? formatDate(authStore.user.created_at) : '-' }}
            </p>
          </div>
        </CardContent>
      </Card>

      <!-- Change Password -->
      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>Update your password to keep your account secure</CardDescription>
        </CardHeader>
        <CardContent>
          <form class="space-y-4" @submit.prevent="onPasswordSubmit">
            <div class="space-y-2">
              <Label for="current_password">Current Password</Label>
              <Input
                id="current_password"
                v-model="currentPasswordField.value.value as string"
                type="password"
                :aria-invalid="currentPasswordField.errorMessage.value ? 'true' : undefined"
                :disabled="savingPassword"
              />
              <p v-if="currentPasswordField.errorMessage.value" class="text-sm text-destructive">
                {{ currentPasswordField.errorMessage.value }}
              </p>
            </div>

            <div class="space-y-2">
              <Label for="new_password">New Password</Label>
              <Input
                id="new_password"
                v-model="newPasswordField.value.value as string"
                type="password"
                :aria-invalid="newPasswordField.errorMessage.value ? 'true' : undefined"
                :disabled="savingPassword"
              />
              <p v-if="newPasswordField.errorMessage.value" class="text-sm text-destructive">
                {{ newPasswordField.errorMessage.value }}
              </p>
              <p class="text-xs text-muted-foreground">
                Password must be at least 8 characters long
              </p>
            </div>

            <div class="space-y-2">
              <Label for="confirm_password">Confirm New Password</Label>
              <Input
                id="confirm_password"
                v-model="confirmPasswordField.value.value as string"
                type="password"
                :aria-invalid="confirmPasswordField.errorMessage.value ? 'true' : undefined"
                :disabled="savingPassword"
              />
              <p v-if="confirmPasswordField.errorMessage.value" class="text-sm text-destructive">
                {{ confirmPasswordField.errorMessage.value }}
              </p>
            </div>

            <Button type="submit" :disabled="savingPassword">
              <Icon v-if="savingPassword" name="Loader" :size="16" class="animate-spin" />
              {{ savingPassword ? 'Updating...' : 'Update Password' }}
            </Button>
          </form>
        </CardContent>
      </Card>
    </template>
  </section>
</template>
