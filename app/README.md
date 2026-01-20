# TinyBase Admin UI

Modern Vue 3 admin interface for TinyBase.

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

The admin UI will be available at http://localhost:5173 (or another port if 5173 is busy).

In development, it proxies API requests to the TinyBase backend running on http://localhost:8000.

### Building for Production

```bash
# Build for production
yarn build

# Preview production build locally
yarn preview
```

The built files in `dist/` should be copied to `../tinybase/admin_static/` for deployment with TinyBase.

## Type-Safe API Client

The frontend uses a generated TypeScript client from the backend's OpenAPI spec for type safety and auto-completion.

### Regenerating the Client

When the backend API changes:

1. Ensure TinyBase server is running: `tinybase serve`
2. Run: `yarn generate:client`

The generated client is in `src/client/` (gitignored, regenerate as needed).

## Tech Stack

- **Vue 3** - Progressive framework
- **Pinia** - State management
- **Vue Router** - Routing
- **Vite** - Build tool & dev server
- **PicoCSS** - Minimal CSS framework
- **Axios** - HTTP client (via generated client)
- **Chart.js** - Data visualization
- **VeeValidate + Yup** - Form validation
