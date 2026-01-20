/**
 * TinyBase Admin UI Entry Point
 *
 * Initializes the Vue 3 application with Pinia state management
 * and Vue Router for navigation.
 */

import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import router from "./router";

// Import Tailwind CSS and base styles
import "./index.css";

import Toast, { PluginOptions, POSITION } from "vue-toastification";
import "vue-toastification/dist/index.css";

// Create Vue app
const app = createApp(App);

const toastOptions: PluginOptions = {
  position: POSITION.TOP_RIGHT,
  timeout: 3000,
  closeOnClick: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.5,
  hideProgressBar: false,
};

// Install plugins
app.use(createPinia());
app.use(router);
app.use(Toast, toastOptions);
// Mount app
app.mount("#app");
