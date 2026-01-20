#!/usr/bin/env node
/**
 * Generate TypeScript API client from TinyBase OpenAPI spec.
 * 
 * Prerequisites:
 * - TinyBase server must be running on http://localhost:8000
 * - Run: tinybase serve (in the project root)
 */

import { existsSync, rmSync, mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const APP_DIR = join(__dirname, '..');
const CLIENT_DIR = join(APP_DIR, 'src', 'client');
const SERVER_URL = 'http://localhost:8000';

/**
 * Check if server is running
 */
async function checkServer() {
  try {
    const response = await fetch(`${SERVER_URL}/health`);
    if (response.ok) {
      console.log('✓ TinyBase server is running');
      return true;
    }
  } catch (error) {
    console.error('✗ TinyBase server is not running');
    console.error('  Please start it with: tinybase serve');
    process.exit(1);
  }
}

/**
 * Generate TypeScript client using @hey-api/openapi-ts
 */
async function generateClient() {
  console.log('Generating TypeScript client from OpenAPI spec...');
  
  // Clear existing client directory
  if (existsSync(CLIENT_DIR)) {
    console.log('Removing existing client directory...');
    rmSync(CLIENT_DIR, { recursive: true, force: true });
  }

  // Create client directory
  mkdirSync(CLIENT_DIR, { recursive: true });

  // Import and run the generator
  const { createClient } = await import('@hey-api/openapi-ts');
  
  await createClient({
    input: `${SERVER_URL}/openapi.json`,
    output: CLIENT_DIR,
    client: '@hey-api/client-axios',
  });

  console.log(`✓ Client generated at ${CLIENT_DIR}`);
}

/**
 * Main execution
 */
async function main() {
  try {
    await checkServer();
    await generateClient();
    console.log('\n✓ Client generation complete!');
    console.log('  You can now import from "~/client" in your TypeScript files');
  } catch (error) {
    console.error('\n✗ Client generation failed:', error.message);
    process.exit(1);
  }
}

main();
