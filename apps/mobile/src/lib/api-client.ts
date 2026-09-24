import { supabase } from '@lib/supabase/client';
import { resolveHostname } from '@lib/utils/network';
import { ApiClient } from '@infrss/shared';
import { getSettings, useSettingsStore } from '@stores/settings';

/**
 * Configure the API client with the current settings from the store.
 * This function should be called:
 * - On app startup (after store rehydration)
 * - When settings are updated (instance switch)
 * - After login/logout
 */
export function configureApiClient(infrssUrl?: string) {
  const settings = getSettings();
  const apiBaseUrl = resolveHostname(
    infrssUrl || settings?.infrss_url || 'http://localhost:8008'
  );

  console.log('[API] Configuring with baseUrl:', apiBaseUrl);

  ApiClient.configure({
    baseUrl: apiBaseUrl,
    getAuthToken: async () => {
      if (!supabase) {
        console.warn('[API] No Supabase client available');
        return null;
      }

      // Supabase getSession already refreshes expiring tokens and deduplicates
      // refresh requests. Refreshing again here churns short-lived sessions.
      const {
        data: { session },
      } = await supabase.auth.getSession();

      return session?.access_token ?? null;
    },
  });
}

// Listen for settings changes to reconfigure client
if (typeof useSettingsStore !== 'undefined') {
  useSettingsStore.subscribe((state, previousState) => {
    if (state.settings.infrss_url !== previousState.settings.infrss_url) {
      configureApiClient(state.settings.infrss_url);
    }
  });
}
