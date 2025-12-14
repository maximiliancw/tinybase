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

// Import PicoCSS
import "@picocss/pico/css/pico.min.css";

// Import custom styles (single entry point)
import "./static/index.css";

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
  showCloseButtonOnHover: true,
  hideProgressBar: false,
};

// Install plugins
app.use(createPinia());
app.use(router);
app.use(Toast, toastOptions);
// Mount app
app.mount("#app");
