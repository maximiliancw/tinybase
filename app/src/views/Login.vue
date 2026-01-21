<script setup lang="ts">
/**
 * Login View
 *
 * Admin authentication page.
 */
import { ref, onMounted } from 'vue';
import { useToast } from '../composables/useToast';
import { useRouter, useRoute } from 'vue-router';
import { useForm, useField } from 'vee-validate';
import { useAuthStore } from '../stores/auth';
import { validationSchemas } from '../composables/useFormValidation';
import { api } from '@/api';
import Icon from '../components/Icon.vue';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const toast = useToast();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const needsSetup = ref(false);
const checkingSetup = ref(true);

const { handleSubmit } = useForm({
  validationSchema: validationSchemas.login,
  initialValues: {
    email: '',
    password: '',
  },
});

const emailField = useField('email');
const passwordField = useField('password');

const onSubmit = handleSubmit(async (values) => {
  const success = await authStore.login(values.email, values.password);

  if (success) {
    // Redirect to intended destination or dashboard
    const redirect = (route.query.redirect as string) || '/';
    router.push(redirect);
  } else {
    toast.error(authStore.error || 'Login failed');
  }
});

onMounted(async () => {
  // Fetch instance name and setup status in parallel
  await Promise.all([
    authStore.fetchInstanceInfo(),
    api.auth
      .getSetupStatus()
      .then((response) => {
        needsSetup.value = response.data?.needs_setup || false;
      })
      .catch(() => {
        /* Ignore errors */
      }),
  ]);
  checkingSetup.value = false;
});
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-6 bg-background">
    <Card class="w-full max-w-md">
      <CardHeader class="space-y-2 text-center">
        <div
          class="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary/80 shadow-lg"
        >
          <Icon name="Box" :size="28" class="text-primary-foreground" />
        </div>
        <h1
          class="text-2xl font-bold bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent"
        >
          {{ authStore.instanceName }}
        </h1>
        <p class="text-sm text-muted-foreground">Admin Dashboard</p>
      </CardHeader>

      <CardContent>
        <!-- First-time setup notice -->
        <Alert v-if="needsSetup && !checkingSetup" class="mb-6">
          <Icon name="ThumbsUp" :size="18" />
          <AlertTitle>Welcome!</AlertTitle>
          <AlertDescription>
            No users exist yet. Enter your credentials to create the first admin account.
          </AlertDescription>
        </Alert>

        <form class="space-y-4" @submit.prevent="onSubmit">
          <div class="space-y-2">
            <Label for="email">Email</Label>
            <Input
              id="email"
              v-model="emailField.value.value"
              type="email"
              placeholder="admin@example.com"
              autocomplete="email"
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
              placeholder="••••••••"
              autocomplete="current-password"
              :aria-invalid="passwordField.errorMessage.value ? 'true' : undefined"
            />
            <p v-if="passwordField.errorMessage.value" class="text-sm text-destructive">
              {{ passwordField.errorMessage.value }}
            </p>
          </div>

          <Button type="submit" class="w-full" :disabled="authStore.loading">
            {{
              authStore.loading
                ? 'Signing in...'
                : needsSetup
                  ? 'Create Admin & Sign In'
                  : 'Sign In'
            }}
          </Button>
        </form>
      </CardContent>

      <CardFooter class="justify-center border-t">
        <p class="text-xs text-muted-foreground">Powered by TinyBase</p>
      </CardFooter>
    </Card>
  </div>
</template>
