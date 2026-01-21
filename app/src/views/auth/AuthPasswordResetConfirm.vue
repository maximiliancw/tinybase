<script setup lang="ts">
/**
 * Auth Portal Password Reset Confirm View
 *
 * Allows users to set a new password using a reset token.
 */
import { ref, onMounted } from "vue";
import { useToast } from "../../composables/useToast";
import { useRoute, useRouter } from "vue-router";
import { api } from "@/api";
import { usePortalStore } from "../../stores/portal";
import { usePreviewParams } from "../../composables/usePreviewParams";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const toast = useToast();
const route = useRoute();
const router = useRouter();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const token = ref<string>("");
const password = ref("");
const confirmPassword = ref("");
const loading = ref(false);

onMounted(async () => {
  await portalStore.fetchConfig();

  // Get token from route params
  token.value = route.params.token as string;

  if (!token.value) {
    toast.error("Invalid reset token");
  }
});

async function handleResetPassword() {
  loading.value = true;

  // Validate passwords match
  if (password.value !== confirmPassword.value) {
    toast.error("Passwords do not match");
    loading.value = false;
    return;
  }

  try {
    await api.auth.confirmPasswordReset({
      body: {
        token: token.value,
        password: password.value,
      },
    });

    toast.success("Password reset successful! Redirecting to login...");

    // Redirect to login after 2 seconds
    setTimeout(() => {
      router.push(withPreviewParams("/auth/login"));
    }, 2000);
  } catch (err: any) {
    toast.error(err.error?.detail || "Failed to reset password");
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
        >
        <h1 class="text-2xl font-bold">
          {{ portalStore.config.instance_name }}
        </h1>
        <p class="text-sm text-muted-foreground">
          Set your new password
        </p>
      </CardHeader>

      <CardContent>
        <form
          class="space-y-4"
          @submit.prevent="handleResetPassword"
        >
          <div class="space-y-2">
            <Label for="password">New Password</Label>
            <Input
              id="password"
              v-model="password"
              type="password"
              placeholder="••••••••"
              required
              autocomplete="new-password"
              minlength="8"
            />
            <p class="text-xs text-muted-foreground">
              Must be at least 8 characters
            </p>
          </div>

          <div class="space-y-2">
            <Label for="confirmPassword">Confirm New Password</Label>
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

          <Button
            type="submit"
            class="w-full"
            :disabled="loading || !token"
          >
            {{ loading ? "Resetting..." : "Reset Password" }}
          </Button>
        </form>

        <div class="mt-4 text-center text-sm">
          <router-link
            :to="withPreviewParams('/auth/login')"
            class="text-primary hover:underline"
          >
            Back to sign in
          </router-link>
        </div>
      </CardContent>

      <CardFooter class="justify-center">
        <p class="text-xs text-muted-foreground">
          Powered by TinyBase
        </p>
      </CardFooter>
    </Card>
  </div>
</template>
