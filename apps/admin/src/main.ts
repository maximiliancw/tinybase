/**
 * TinyBase Admin UI Entry Point
 *
 * Initializes the Vue 3 application with Pinia state management
 * and Vue Router for navigation.
 */

import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import router from './router';

// Import Tailwind CSS and base styles
import './index.css';

// Create Vue app
const app = createApp(App);

// Install plugins
app.use(createPinia());
app.use(router);

// Mount app
app.mount('#app');
