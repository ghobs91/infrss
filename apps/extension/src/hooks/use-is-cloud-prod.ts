import { useExtensionStore } from '@/store'

/**
 * Hook to determine if the extension is connected to the cloud production instance
 * Returns true if infrss_url is set to the production API URL
 */
export function useIsCloudProd(): boolean {
  const settings = useExtensionStore((state) => state.settings)

  // Check if the infrss_url matches the production API URL
  return settings.infrss_url === 'https://api.readspace.ai'
}
