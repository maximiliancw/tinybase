<script setup lang="ts">
/**
 * Auth Portal Register View
 *
 * Public-facing registration page.
 */
import { ref, onMounted } from 'vue';
import { useToast } from '../../composables/useToast';
import { useRouter, useRoute } from 'vue-router';
import { api } from '@/api';
import { usePortalStore } from '../../stores/portal';
import { usePreviewParams } from '../../composables/usePreviewParams';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const toast = useToast();
const router = useRouter();
const route = useRoute();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const loading = ref(false);

function isValidAbsoluteUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

onMounted(async () => {
  await portalStore.fetchConfig();

  // Redirect if registration is disabled
  if (!portalStore.config.registration_enabled) {
    router.push(withPreviewParams('/auth/login'));
  }
});

async function handleRegister() {
  loading.value = true;

  // Validate passwords match
  if (password.value !== confirmPassword.value) {
    toast.error('Passwords do not match');
    loading.value = false;
    return;
  }

  try {
    await api.auth.register({
      body: {
        email: email.value,
        password: password.value,
      },
    });

    toast.success('Registration successful! Redirecting...');

    // Clear form
    email.value = '';
    password.value = '';
    confirmPassword.value = '';

    // Get redirect URL
    const redirectParam = route.query.redirect as string | undefined;
    const configuredUrl = portalStore.config.register_redirect_url;

    let redirectUrl: string | null = null;
    if (redirectParam && isValidAbsoluteUrl(redirectParam)) {
      redirectUrl = redirectParam;
    } else if (configuredUrl && isValidAbsoluteUrl(configuredUrl)) {
      redirectUrl = configuredUrl;
    }

    // Redirect after 1 second
    setTimeout(() => {
      if (redirectUrl && isValidAbsoluteUrl(redirectUrl)) {
        window.location.href = redirectUrl;
      } else {
        toast.error(
          'Registration successful, but redirect URL is not configured. Please contact your administrator.'
        );
      }
    }, 1000);
  } catch (err: any) {
    toast.error(err.error?.detail || 'Registration failed');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-6 bg-background">
    <Card class="w-full max-w-md">
      <CardHeader class="space-y-2 text-center">
        <img
          v-if="portalStore.config.logo_url"
          :src="portalStore.config.logo_url"
          alt="Logo"
          class="mx-auto h-12 w-auto"
        />
        <h1 class="text-2xl font-bold">
          {{ portalStore.config.instance_name }}
        </h1>
        <p class="text-sm text-muted-foreground">Create a new account</p>
      </CardHeader>

      <CardContent>
        <form class="space-y-4" @submit.prevent="handleRegister">
          <div class="space-y-2">
            <Label for="email">Email</Label>
            <Input
              id="email"
              v-model="email"
              type="email"
              placeholder="user@example.com"
              required
              autocomplete="email"
            />
          </div>

          <div class="space-y-2">
            <Label for="password">Password</Label>
            <Input
              id="password"
              v-model="password"
              type="password"
              placeholder="••••••••"
              required
              autocomplete="new-password"
              minlength="8"
            />
            <p class="text-xs text-muted-foreground">Must be at least 8 characters</p>
          </div>

          <div class="space-y-2">
            <Label for="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              placeholder="••••••••"
              required
              autocomplete="new-password"
              minlength="8"
            />
          </div>

          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? 'Creating account...' : 'Create Account' }}
          </Button>
        </form>

        <div class="mt-4 text-center text-sm">
          <router-link :to="withPreviewParams('/auth/login')" class="text-primary hover:underline">
            Already have an account? Sign in
          </router-link>
        </div>
      </CardContent>

      <CardFooter class="justify-center">
        <p class="text-xs text-muted-foreground">Powered by TinyBase</p>
      </CardFooter>
    </Card>
  </div>
</template>
