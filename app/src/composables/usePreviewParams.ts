/**
 * Composable for handling preview parameters in auth portal routes
 *
 * Preserves preview parameters (preview, logo_url, primary_color, background_image_url, token)
 * when navigating between auth portal routes.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

export function usePreviewParams() {
  const route = useRoute();

  // Check if we're in preview mode
  const isPreview = computed(() => {
    return route.query.preview === "true";
  });

  // Get all preview-related query parameters
  const previewParams = computed(() => {
    const params: Record<string, string> = {};
    if (route.query.preview === "true") {
      params.preview = "true";
      if (route.query.logo_url)
        params.logo_url = route.query.logo_url as string;
      if (route.query.primary_color)
        params.primary_color = route.query.primary_color as string;
      if (route.query.background_image_url)
        params.background_image_url = route.query
          .background_image_url as string;
      if (route.query.token) params.token = route.query.token as string;
    }
    return params;
  });

  // Generate a route location object with preview params preserved
  function withPreviewParams(
    to: string | { path: string; params?: Record<string, any> }
  ) {
    const path = typeof to === "string" ? to : to.path;
    const routeParams = typeof to === "object" && to.params ? to.params : {};

    return {
      path,
      params: routeParams,
      query: {
        ...previewParams.value,
      },
    };
  }

  return {
    isPreview,
    previewParams,
    withPreviewParams,
  };
}
