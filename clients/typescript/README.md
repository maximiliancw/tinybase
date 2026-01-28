# TinyBase TypeScript Client

This is an **auto-generated** TypeScript API client for TinyBase.

## Purpose

This client provides typed HTTP bindings for the TinyBase REST API. It is intended for:

- Frontend applications (SPAs, SSR apps)
- Node.js applications that need to interact with a TinyBase backend
- The TinyBase Admin UI (`apps/admin/`)

**Note:** This is NOT a full SDK. It's a thin, auto-generated client. For server-side function development in Python, use the `tinybase-sdk` package instead.

## Generation

The client is generated from `openapi/openapi.json` using [openapi-typescript](https://github.com/drwpow/openapi-typescript).

To regenerate:

```bash
cd clients/typescript
npm install
npm run generate
```

Or from the repo root:

```bash
make generate-ts-client
```

## Usage

```typescript
import { createClient } from '@tinybase/client';

const client = createClient({
  baseUrl: 'http://localhost:8000',
});

// Use typed API methods
const response = await client.GET('/api/collections');
```

## CI Integration

The TypeScript client is regenerated automatically by CI when the OpenAPI spec changes. Do not manually edit the generated files in `src/`.
