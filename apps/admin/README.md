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

### Code Quality

```bash
# Lint code
yarn lint

# Auto-fix linting issues
yarn lint:fix

# Format code with Prettier
yarn format

# Check formatting
yarn format:check
```

### Building for Production

```bash
# Build for production
yarn build

# Preview production build locally
yarn preview
```

> Note: The built files in `dist/` should be copied to `PROJECT_ROOT/tinybase/static/app/` for integrated deployment with TinyBase. Per default, this happens automatically during the Docker build process.

## Type-Safe API Client

The frontend uses an **auto-generated TypeScript client** created from TinyBase's OpenAPI specification using [@hey-api/openapi-ts](https://heyapi.dev/openapi-ts/). This provides full type safety, auto-completion, and ensures the frontend stays in sync with the backend API.

### Generated Client

The client is located at `src/client/` (gitignored) and includes:

- `sdk.gen.ts` - Service classes organized by OpenAPI tags (Auth, Collections, Functions, etc.)
- `types.gen.ts` - TypeScript types for all requests/responses
- `client.gen.ts` - Configured Axios client instance

### Configuration

The client is configured in two files:

- `src/client-config.ts` - Runtime configuration (auth, base URL, interceptors)
- `src/api.ts` - Exports configured client instance and types

Configuration includes automatic:

- JWT authentication (bearer tokens from localStorage)
- 401 error handling with automatic logout
- Base URL configuration via `VITE_API_URL` environment variable

### Regenerating the Client

Whenever the backend API changes, regenerate the client:

```bash
# 1. Start TinyBase server
tinybase serve

# 2. Regenerate the client (requires server running)
yarn generate:client
```

The `dev` and `build` scripts automatically check if the client exists and warn if regeneration is needed.

### Usage Examples

```typescript
// Import the configured API client
import { api } from '@/api'

// Auth service
const loginResponse = await api.auth.login({
  body: { email: 'user@example.com', password: 'password123' }
})
const user = await api.auth.getMe()

// Collections service
const collections = await api.collections.listCollections()
const records = await api.collections.listRecords({
  path: { collection_name: 'users' },
  query: { limit: 10, offset: 0 }
})

// Functions service
const result = await api.functions.callFunction({
  path: { function_name: 'hello' },
  body: { name: 'World' }
})

// Import types
import type { 
  TinybaseApiRoutesAuthUserInfo,
  CollectionResponse,
  RecordResponse,
  FunctionInfo
} from '@/client'
```

## Tech Stack

### Core Framework

- **Vue 3** - Progressive JavaScript framework with Composition API
- **Pinia** - State management for Vue 3
- **Vue Router** - Client-side routing
- **Vite** - Build tool & dev server

### UI & Styling

- **shadcn-vue** - Modern UI component library
- **Tailwind CSS** - Utility-first CSS framework
- **Reka UI** - Unstyled, accessible component primitives
- **Lucide Icons** - Icon library
- **Unovis** - Data visualization

### API & Data

- **@hey-api/openapi-ts** - OpenAPI client generator with SDK support
- **Axios** - HTTP client (via generated client)

### Forms & Validation

- **VeeValidate** - Form validation
- **Yup** - Schema validation

### Development Tools

- **TypeScript** - Type safety
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **VueUse** - Collection of composition utilities
