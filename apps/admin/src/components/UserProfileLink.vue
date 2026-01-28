<script setup lang="ts">
/**
 * UserProfileLink Component
 *
 * Displays the current user's email with a link to their profile page.
 * Reusable across sidebar and mobile header.
 */
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import Icon from './Icon.vue';

interface Props {
  /** Additional CSS classes for the container */
  class?: string;
}

defineProps<Props>();

const authStore = useAuthStore();
</script>

<template>
  <div class="flex items-center gap-2 text-sm min-w-0 overflow-hidden" :class="$props.class">
    <Icon name="User" :size="18" class="shrink-0" />
    <RouterLink
      to="/admin/profile"
      class="hover:underline text-muted-foreground truncate"
      active-class="bg-accent/50 text-primary underline"
    >
      {{ authStore.user?.email }}
    </RouterLink>
  </div>
</template>
