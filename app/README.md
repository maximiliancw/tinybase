# TinyBase Admin

Modern admin user interface for TinyBase instances built with Vue, Vite, shadcn, and TailwindCSS.

## Development

### Prerequisites

- Node.js 18+ and Yarn
- TinyBase backend running (see parent directory)

### Setup

```bash
# Install dependencies
yarn install

# Generate TypeScript API client from backend
# (Requires TinyBase server running on http://localhost:8000)
yarn generate:client
```

### Running

```bash
# Start dev server with hot reload
yarn dev
```

The admin UI will be available at <http://localhost:5173> (or another port if 5173 is busy).

In development, it proxies API requests to the TinyBase backend running on <http://localhost:8000>.

### Building for Production

```bash
# Build for production
yarn build

# Preview production build locally
yarn preview
```

> Note: The built files in `dist/` should be copied to `PROJECT_ROOT/tinybase/admin_static/` for integrated deployment with TinyBase.

## Type-Safe API Client

The frontend uses an **auto-generated TypeScript client** created from TinyBase's OpenAPI specification. This provides full type safety, auto-completion, and ensures the frontend stays in sync with the backend API.

### Generated Client

The client is located at `src/client/` (gitignored) and includes:

- `services.gen.ts` - All API endpoint functions
- `types.gen.ts` - TypeScript types for requests/responses
- `schemas.gen.ts` - Schema definitions

The client is configured in `src/api/index.ts` with automatic:

- JWT authentication (bearer tokens)
- Error handling (401 redirects)
- Base URL configuration via `VITE_API_URL`

### Regenerating the Client

Whenever the backend API changes, regenerate the client:

```bash
# 1. Start TinyBase server
tinybase serve

# 2. Regenerate the client
yarn generate:client
```

### Usage Examples

```typescript
// Import service functions and types
import { 
  loginApiAuthLoginPost,
  getMeApiAuthMeGet,
  listCollectionsApiCollectionsGet,
  type User,
  type Collection
} from '@/api'

// Call API with full type safety
const response = await loginApiAuthLoginPost({
  body: {
    email: 'user@example.com',
    password: 'password123'
  }
})

// Backward compatibility - raw axios instance
import { api } from '@/api'
const response = await api.get('/api/auth/me')
```

## Tech Stack

- **Vue 3** - Progressive JavaScript framework with Composition API
- **Pinia** - State management for Vue 3
- **Vue Router** - Client-side routing
- **Vite** - Build tool & dev server
- **shadcn-vue** - Modern UI component library
- **Tailwind CSS** - Utility-first CSS framework
- **Reka UI** - Unstyled, accessible component primitives
- **@hey-api/openapi-ts** - OpenAPI client generator for Typescript
- **Axios** - HTTP client (via generated client)
- **Unovis** - Data visualization
- **VeeValidate + Zod** - Form validation
- **VueUse** - Collection of composition utilities
- **Lucide Icons** - Icon library
