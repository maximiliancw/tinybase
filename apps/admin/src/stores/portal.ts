/**
 * Portal Store
 *
 * Manages portal configuration (instance name, logo, colors)
 * and applies them to the UI.
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '@/api';
import type { PortalConfigResponse } from '@/client';
import { client as baseClient } from '../client/client.gen';

export const usePortalStore = defineStore('portal', () => {
  const config = ref<PortalConfigResponse>({
    instance_name: 'TinyBase',
    logo_url: null,
    primary_color: null,
    background_image_url: null,
    registration_enabled: true,
    login_redirect_url: null,
    register_redirect_url: null,
  });

  const loading = ref(false);
  const error = ref<string | null>(null);

  // Computed styles based on config
  const styles = computed(() => {
    const style: Record<string, string> = {};
    if (config.value.background_image_url) {
      style['--auth-background-image'] = `url(${config.value.background_image_url})`;
    }
    if (config.value.primary_color) {
      // Apply primary color to CSS variables
      style['--auth-primary-color'] = config.value.primary_color;
    }
    return style;
  });

  async function fetchConfig() {
    loading.value = true;
    error.value = null;

    try {
      // Check for preview parameters in URL
      const urlParams = new URLSearchParams(window.location.search);
      const isPreview = urlParams.get('preview') === 'true';

      if (isPreview) {
        const queryParams: Record<string, string> = {
          preview: 'true',
        };

        // Get preview values from URL
        const logoUrl = urlParams.get('logo_url');
        const primaryColor = urlParams.get('primary_color');
        const backgroundImageUrl = urlParams.get('background_image_url');

        if (logoUrl !== null) queryParams.logo_url = logoUrl;
        if (primaryColor !== null) queryParams.primary_color = primaryColor;
        if (backgroundImageUrl !== null) queryParams.background_image_url = backgroundImageUrl;

        // If token is provided in URL (for iframe preview), add it to client
        const previewToken = urlParams.get('token');
        if (previewToken) {
          const response = await api.auth.getPortalConfig({
            query: queryParams,
            client: {
              ...baseClient,
              getConfig: () => ({
                ...baseClient.getConfig(),
                headers: {
                  ...baseClient.getConfig().headers,
                  Authorization: `Bearer ${previewToken}`,
                },
              }),
            },
          });
          config.value = response.data as PortalConfigResponse;
        } else {
          const response = await api.auth.getPortalConfig({
            query: queryParams,
          });
          config.value = response.data as PortalConfigResponse;
        }
      } else {
        const response = await api.auth.getPortalConfig();
        config.value = response.data as PortalConfigResponse;
      }
    } catch (err: any) {
      error.value = err.error?.detail || 'Failed to load portal configuration';
      console.error('Failed to fetch portal config:', err);
    } finally {
      loading.value = false;
    }
  }

  return {
    config,
    loading,
    error,
    styles,
    fetchConfig,
  };
});
