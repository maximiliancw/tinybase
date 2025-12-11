<script setup lang="ts">
/**
 * Icon Component
 *
 * Wrapper component for Lucide icons with consistent styling.
 * Provides a simple interface for using icons throughout the application.
 *
 * Usage:
 *   <Icon name="X" :size="20" />
 *   <Icon name="Settings" color="var(--tb-primary)" />
 *
 * Note: This component imports all Lucide icons for convenience. For optimal
 * bundle size in production, import icons directly:
 *   import { X, Settings } from 'lucide-vue-next';
 */
import { computed, shallowRef } from "vue";
import * as LucideIcons from "lucide-vue-next";

interface Props {
  /** Name of the icon (e.g., 'X', 'Settings', 'User') */
  name: string;
  /** Size of the icon in pixels (default: 24) */
  size?: number;
  /** Color of the icon (default: currentColor) */
  color?: string;
  /** Stroke width (default: 2) */
  strokeWidth?: number;
  /** Additional CSS classes */
  class?: string;
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  color: "currentColor",
  strokeWidth: 2,
  class: "",
});

// Icon name mapping for common aliases
const iconNameMap: Record<string, string> = {
  X: "X",
  Close: "X",
  Settings: "Settings",
  User: "User",
  Users: "Users",
  Dashboard: "LayoutDashboard",
  Collection: "Folder",
  Collections: "Folder",
  File: "File",
  Files: "File",
  Function: "Zap",
  Functions: "Zap",
  Schedule: "Clock",
  Schedules: "Clock",
  Extension: "Puzzle",
  Extensions: "Puzzle",
  Logout: "LogOut",
  Login: "LogIn",
  Arrow: "ArrowRight",
  Plus: "Plus",
  Minus: "Minus",
  Edit: "Edit",
  Delete: "Trash2",
  Save: "Save",
  Cancel: "X",
  // Additional icons used throughout the app
  Box: "Box",
  FolderPlus: "FolderPlus",
  UserPlus: "UserPlus",
  ExternalLink: "ExternalLink",
  Power: "Power",
  PowerOff: "PowerOff",
  Trash2: "Trash2",
  ThumbsUp: "ThumbsUp",
  AlertCircle: "AlertCircle",
  CheckCircle: "CheckCircle",
  List: "List",
};

const IconComponent = computed(() => {
  // Capitalize first letter and handle common variations
  const iconName = props.name.charAt(0).toUpperCase() + props.name.slice(1);
  const resolvedName = iconNameMap[iconName] || iconName;
  const component = (LucideIcons as any)[resolvedName];

  if (!component) {
    console.warn(
      `Icon "${props.name}" (resolved as "${resolvedName}") not found in Lucide`
    );
    return null;
  }

  return component;
});
</script>

<template>
  <component
    v-if="IconComponent"
    :is="IconComponent"
    :size="size"
    :color="color"
    :stroke-width="strokeWidth"
    :class="class"
  />
  <span
    v-else
    class="icon-placeholder"
    :style="{ fontSize: `${size * 0.75}px` }"
  >
    ?
  </span>
</template>

<style scoped>
.icon-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.5;
  color: currentColor;
}
</style>
