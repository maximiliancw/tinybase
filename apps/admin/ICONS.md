# Icon Library Usage Guide

This project uses [Lucide Vue Next](https://lucide.dev/guide/packages/lucide-vue-next) - a lightweight, extensive icon library with 1000+ free-to-use icons.

## Quick Start

### Direct Import (Recommended for Production)

For optimal bundle size and tree-shaking, import icons directly:

```vue
<script setup>
import { X, Settings, User } from 'lucide-vue-next';
</script>

<template>
  <X :size="20" />
  <Settings color="var(--tb-primary)" />
  <User :stroke-width="2.5" />
</template>
```

### Using the Icon Component (Convenient, but larger bundle)

The `Icon` component provides a simple wrapper for easy icon usage. **Note:** This imports all icons, which increases bundle size. Use for development/prototyping, but prefer direct imports for production.

```vue
<script setup>
import Icon from '@/components/Icon.vue';
</script>

<template>
  <Icon name="X" :size="20" />
  <Icon name="Settings" color="var(--tb-primary)" />
  <Icon name="User" :stroke-width="2.5" />
</template>
```

## Icon Component Props

- `name` (required): Icon name (e.g., "X", "Settings", "User")
- `size` (optional, default: 24): Icon size in pixels (use `:size="20"` for numbers)
- `color` (optional, default: "currentColor"): Icon color
- `strokeWidth` (optional, default: 2): Stroke width
- `class` (optional): Additional CSS classes

## Common Icon Names

The Icon component supports common aliases:

- `X` or `Close` → X icon
- `Settings` → Settings icon
- `User` / `Users` → User/Users icons
- `Dashboard` → LayoutDashboard icon
- `Collection` / `Collections` → Folder icon
- `File` / `Files` → File icon
- `Function` / `Functions` → Zap icon
- `Schedule` / `Schedules` → Clock icon
- `Extension` / `Extensions` → Puzzle icon
- `Logout` → LogOut icon
- `Login` → LogIn icon
- `Plus`, `Minus`, `Edit`, `Delete`, `Save`, etc.

## Finding Icons

Browse all available icons at: https://lucide.dev/icons/

Icon names in Lucide use PascalCase (e.g., `LayoutDashboard`, `LogOut`, `Trash2`). The Icon component handles common variations automatically.

## Examples

### In Buttons

```vue
<!-- Direct import (recommended) -->
<script setup>
import { Plus } from 'lucide-vue-next';
</script>
<template>
  <button>
    <Plus :size="16" />
    Add Item
  </button>
</template>

<!-- Or using Icon component -->
<script setup>
import Icon from '@/components/Icon.vue';
</script>
<template>
  <button>
    <Icon name="Plus" :size="16" />
    Add Item
  </button>
</template>
```

### In Navigation

```vue
<script setup>
import { Settings } from 'lucide-vue-next';
</script>
<template>
  <router-link to="/settings">
    <Settings :size="20" />
    Settings
  </router-link>
</template>
```

### With Custom Styling

```vue
<script setup>
import { User } from 'lucide-vue-next';
</script>
<template>
  <User 
    :size="32" 
    color="var(--tb-primary)" 
    :stroke-width="2.5"
    class="my-custom-class"
  />
</template>
```
