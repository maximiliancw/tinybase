<script setup lang="ts">
/**
 * Auth Portal Login View
 *
 * Public-facing login page for users.
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
});

function getRedirectUrl(): string {
  // Check for redirect query parameter first (takes precedence)
  const redirectParam = route.query.redirect as string | undefined;
  if (redirectParam && isValidAbsoluteUrl(redirectParam)) {
    return redirectParam;
  }
  // Use configured redirect URL (required when portal is enabled)
  const configuredUrl = portalStore.config.login_redirect_url;
  if (configuredUrl && isValidAbsoluteUrl(configuredUrl)) {
    return configuredUrl;
  }
  // No valid redirect URL - show error
  throw new Error('No valid redirect URL configured. Please contact your administrator.');
}

async function handleLogin() {
  loading.value = true;

  try {
    const response = await api.auth.login({
      body: {
        email: email.value,
        password: password.value,
      },
    });

    // Store JWT tokens
    localStorage.setItem('tb_access_token', response.data.access_token);
    localStorage.setItem('tb_refresh_token', response.data.refresh_token);

    // Redirect to configured URL or query parameter
    try {
      const redirectUrl = getRedirectUrl();
      // Validate redirect URL - must be absolute URL
      if (isValidAbsoluteUrl(redirectUrl)) {
        window.location.href = redirectUrl;
      } else {
        throw new Error('Invalid redirect URL');
      }
    } catch (err: any) {
      toast.error(
        err.message || 'Redirect configuration error. Please contact your administrator.'
      );
      loading.value = false;
      return;
    }
  } catch (err: any) {
    toast.error(err.error?.detail || 'Login failed');
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
        <p class="text-sm text-muted-foreground">Sign in to your account</p>
      </CardHeader>

      <CardContent>
        <form class="space-y-4" @submit.prevent="handleLogin">
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
              autocomplete="current-password"
            />
          </div>

          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? 'Signing in...' : 'Sign In' }}
          </Button>
        </form>

        <div class="mt-4 flex items-center justify-center gap-2 text-sm">
          <router-link
            :to="withPreviewParams('/auth/password-reset')"
            class="text-primary hover:underline"
          >
            Forgot password?
          </router-link>
          <template v-if="portalStore.config.registration_enabled">
            <span class="text-muted-foreground">|</span>
            <router-link
              :to="withPreviewParams('/auth/register')"
              class="text-primary hover:underline"
            >
              Create account
            </router-link>
          </template>
        </div>
      </CardContent>

      <CardFooter class="justify-center">
        <p class="text-xs text-muted-foreground">Powered by TinyBase</p>
      </CardFooter>
    </Card>
  </div>
</template>
