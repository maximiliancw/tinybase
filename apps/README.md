# Apps

This directory contains frontend applications for TinyBase.

## Structure

```
apps/
└── admin/              # Vue 3 Admin UI
    ├── src/
    │   ├── views/      # Page components
    │   ├── stores/     # Pinia state management
    │   ├── components/ # Reusable UI components
    │   ├── composables/# Vue composables
    │   └── router/     # Vue Router configuration
    ├── public/         # Static assets
    └── package.json    # Node dependencies
```

## Admin UI

The admin interface is a single-page application built with:

- **Vue 3** - Progressive JavaScript framework
- **Pinia** - State management
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/vue** - UI component library

### Development

```bash
cd apps/admin

# Install dependencies
yarn install

# Start dev server (hot reload)
yarn dev
```

The dev server runs at `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

### Building

```bash
# Build for production
yarn build

# Or from repository root
make build-admin
```

Built files are output to `apps/admin/dist/` and automatically copied to `packages/tinybase/tinybase/static/app/` by the Makefile.

### Features

The Admin UI provides:

- **Dashboard** - Overview of collections, users, and function calls
- **Collections** - Create and manage dynamic collections
- **Records** - CRUD operations on collection records
- **Users** - User management and admin promotion
- **Functions** - View registered functions and execution history
- **Schedules** - Create and manage scheduled tasks
- **Settings** - Configure instance-wide settings

### Customization

To use a custom admin UI:

1. Build your custom UI
2. Set the `admin.static_dir` configuration to point to your build directory

```toml
[admin]
static_dir = "/path/to/custom/admin/dist"
```

## Adding New Apps

Future applications (e.g., auth portal, user dashboard) should be added as subdirectories:

```
apps/
├── admin/          # Existing admin UI
├── portal/         # Future: Auth portal
└── dashboard/      # Future: User-facing dashboard
```
