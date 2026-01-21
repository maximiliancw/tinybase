import { TinyBase } from '@/client';
import { client } from '@/client/client.gen';

// client is already configured via runtimeConfigPath + createClientConfig()
export const api = new TinyBase({ client });

// re-export types so components import from one place
export * from '@/client';