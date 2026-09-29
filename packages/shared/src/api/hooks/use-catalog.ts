import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from '@tanstack/react-query';
import { ApiClient } from '../client';
import { queryKeys, RSS_QUERY_KEYS } from '../query-keys';
import type { Subscription } from '../types/feeds';

/** Browse catalogued primary entities. */
export function useCatalogEntitiesQuery(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: queryKeys.catalogEntities(),
    queryFn: () => ApiClient.listCatalogEntities(params),
    staleTime: 5 * 60 * 1000,
  });
}

/** Browse catalog feeds, optionally scoped to one entity. */
export function useCatalogFeedsQuery(entityId: string | null) {
  return useQuery({
    queryKey: queryKeys.catalogFeeds(entityId),
    queryFn: () => ApiClient.listCatalogFeeds({ entityId: entityId ?? undefined }),
    enabled: !!entityId,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Subscribe to a catalog feed, promoting it into the user's library. Invalidates the feeds,
 * articles, unread counts and folders caches (mirrors `useCreateFeed`).
 */
export function useSubscribeCatalogFeedMutation(
  options?: UseMutationOptions<Subscription, unknown, { feedId: string; folderId?: string }>
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ feedId, folderId }) => ApiClient.subscribeCatalogFeed(feedId, folderId),
    onSettled: () => {
      return Promise.all([
        queryClient.invalidateQueries({
          queryKey: [RSS_QUERY_KEYS.FEEDS, 'list'],
          refetchType: 'all',
        }),
        queryClient.invalidateQueries({
          queryKey: [RSS_QUERY_KEYS.ARTICLES],
          refetchType: 'all',
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.unreadCounts(),
          refetchType: 'all',
        }),
        queryClient.invalidateQueries({
          queryKey: [RSS_QUERY_KEYS.FOLDERS],
          refetchType: 'all',
        }),
      ]);
    },
    ...options,
  });
}
