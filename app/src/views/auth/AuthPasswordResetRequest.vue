<script setup lang="ts">
/**
 * Auth Portal Password Reset Request View
 *
 * Allows users to request a password reset email.
 */
import { ref, onMounted } from "vue";
import { useToast } from "../../composables/useToast";
import { usePortalStore } from "../../stores/portal";
import { api } from "../../api";
import { usePreviewParams } from "../../composables/usePreviewParams";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const toast = useToast();
const portalStore = usePortalStore();
const { withPreviewParams } = usePreviewParams();

const email = ref("");
const loading = ref(false);

onMounted(async () => {
  await portalStore.fetchConfig();
});

async function handleRequestReset() {
  loading.value = true;

  try {
    await api.auth.requestPasswordReset({
      body: {
        email: email.value,
      },
    });

    // Always show success message (security best practice)
    toast.success("If that email exists, a password reset link has been sent.");
    email.value = "";
  } catch (err: any) {
    toast.error(
      err.error?.detail || "Failed to request password reset"
    );
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
        <h1 class="text-2xl font-bold">{{ portalStore.config.instance_name }}</h1>
        <p class="text-sm text-muted-foreground">Reset your password</p>
      </CardHeader>

      <CardContent>
        <p class="mb-4 text-sm text-muted-foreground">
          Enter your email address and we'll send you a link to reset your
          password.
        </p>

        <form @submit.prevent="handleRequestReset" class="space-y-4">
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

          <Button
            type="submit"
            class="w-full"
            :disabled="loading"
          >
            {{ loading ? "Sending..." : "Send Reset Link" }}
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
        <p class="text-xs text-muted-foreground">Powered by TinyBase</p>
      </CardFooter>
    </Card>
  </div>
</template>
