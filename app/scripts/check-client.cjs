#!/usr/bin/env node

/**
 * Pre-build/dev validation script
 * 
 * Ensures the auto-generated API client exists before running the app.
 * This prevents runtime errors from missing client imports.
 */

const fs = require('fs');
const path = require('path');

const CLIENT_DIR = path.join(__dirname, '..', 'src', 'client');
const CLIENT_INDEX = path.join(CLIENT_DIR, 'index.ts');

// Check if client directory exists
if (!fs.existsSync(CLIENT_DIR)) {
  console.error('\n❌ ERROR: Auto-generated API client not found!\n');
  console.error('The API client must be generated before running the app.\n');
  console.error('To generate the client:\n');
  console.error('  1. Start the TinyBase server: tinybase serve');
  console.error('  2. Generate the client: yarn generate:client\n');
  process.exit(1);
}

// Check if client index file exists
if (!fs.existsSync(CLIENT_INDEX)) {
  console.error('\n❌ ERROR: Auto-generated API client is incomplete!\n');
  console.error('The client directory exists but appears to be incomplete.\n');
  console.error('To regenerate the client:\n');
  console.error('  1. Start the TinyBase server: tinybase serve');
  console.error('  2. Generate the client: yarn generate:client\n');
  process.exit(1);
}

console.log('✅ API client validation passed');
