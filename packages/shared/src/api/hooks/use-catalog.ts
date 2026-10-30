import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from '@tanstack/react-query';
import { ApiClient } from '../client';
import { CATALOG_QUERY_KEYS, queryKeys, RSS_QUERY_KEYS } from '../query-keys';
import type { CatalogSource } from '../types/catalog';
import type { FeedCategory, Subscription } from '../types/feeds';

/** How often the discover-style source list refreshes while the page is open. */
const CATALOG_SOURCES_REFETCH_INTERVAL_MS = 60 * 1000;

/** The catalog browse has no pagination; fetch every source in one request. */
const CATALOG_SOURCES_LIMIT = 1000;

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
 * Browse every primary source that has verified feeds, for the discover-style catalog view.
 *
 * Continually refreshes: polls every minute while the page is open and refetches when the
 * window regains focus, so newly verified sources appear without a manual reload.
 */
export function useCatalogSourcesQuery(category?: FeedCategory | null) {
  return useQuery<CatalogSource[]>({
    queryKey: queryKeys.catalogSources(category ?? null),
    queryFn: () =>
      ApiClient.listCatalogSources({
        category: category ?? undefined,
        limit: CATALOG_SOURCES_LIMIT,
      }),
    staleTime: 30 * 1000,
    refetchInterval: CATALOG_SOURCES_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: true,
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
    // Flip the card immediately; the settled invalidation below reconciles with the server.
    onMutate: async ({ feedId }) => {
      await queryClient.cancelQueries({ queryKey: [CATALOG_QUERY_KEYS.SOURCES] });
      queryClient.setQueriesData<CatalogSource[]>(
        { queryKey: [CATALOG_QUERY_KEYS.SOURCES] },
        (sources) =>
          sources?.map((source) => ({
            ...source,
            feeds: source.feeds.map((feed) =>
              feed.id === feedId ? { ...feed, is_subscribed: true } : feed
            ),
          }))
      );
    },
    onError: () => {
      return queryClient.invalidateQueries({ queryKey: [CATALOG_QUERY_KEYS.SOURCES] });
    },
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
        queryClient.invalidateQueries({
          queryKey: [CATALOG_QUERY_KEYS.SOURCES],
        }),
      ]);
    },
    ...options,
  });
}
