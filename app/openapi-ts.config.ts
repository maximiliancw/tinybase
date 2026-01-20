import { defineConfig } from '@hey-api/openapi-ts';

/**
 * Hey API OpenAPI TypeScript Generator Configuration
 * 
 * This config generates a service-oriented TypeScript client for TinyBase API.
 * Each OpenAPI tag (auth, collections, functions, etc.) becomes a separate service class.
 * 
 * Documentation: https://heyapi.dev/openapi-ts/configuration
 * SDK Plugin: https://heyapi.dev/openapi-ts/plugins/sdk
 */
export default defineConfig({
  input: 'http://localhost:8000/openapi.json',
  output: {
    path: './src/client',
    // Clean output directory before generating
    clean: true,
    // Use modern ES module syntax
    format: 'prettier',
  },
  plugins: [
    // Core TypeScript types plugin
    {
      name: '@hey-api/typescript',
      // Export enums as const objects for better tree-shaking
      enums: 'javascript',
    },
    // SDK plugin generates service classes organized by tags
    {
      name: '@hey-api/sdk',
      // Use Axios as the HTTP client
      client: '@hey-api/client-axios',
      // Generate service classes organized by OpenAPI tags
      operations: {
        // Use 'single' strategy to generate service classes
        strategy: 'single',
        // Main SDK container class name
        containerName: 'TinyBaseClient',
        // Custom nesting to organize methods by tag into service classes
        nesting(operation) {
          // Get the first tag (e.g., 'auth', 'collections', 'functions')
          const tag = operation.tags?.[0];
          
          if (!tag) {
            // Fallback for untagged operations
            return [
              operation.operationId || 
              operation.method.toLowerCase()
            ];
          }
          
          // Extract method name from operationId by removing tag prefix
          // e.g., 'auth_get_instance_info' -> 'getInstanceInfo'
          const operationId = operation.operationId || '';
          const tagPrefix = `${tag}_`;
          
          let methodName = operationId;
          if (operationId.startsWith(tagPrefix)) {
            // Remove tag prefix
            methodName = operationId.substring(tagPrefix.length);
          }
          
          // Convert snake_case to camelCase
          methodName = methodName.replace(/_([a-z])/g, (_, letter) => 
            letter.toUpperCase()
          );
          
          // Return [serviceName, methodName]
          // This creates: client.auth.getInstanceInfo()
          return [tag, methodName];
        },
      },
    },
  ],
});
