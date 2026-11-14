"use client"

import { useQueryClient } from "@tanstack/react-query"
import { queryKeys, RSS_QUERY_KEYS, useRefreshFeed } from "@infrss/shared"
import { useCallback, useRef, useState } from "react"

/**
 * Pull-to-refresh / header refresh for the article list.
 *
 * Mirrors the native app: when a single feed is open, force a fetch from its source first (so
 * a manual refresh can actually find new articles), then revalidate the article lists, unread
 * counts and feed list with `refetchType: 'active'` so the global staleTime doesn't hand back
 * cache. Other scopes (All/folders) just revalidate — the background worker owns
 * refreshing every subscription, and firing per-feed requests for a whole folder is far too
 * many round trips for one gesture.
 */
export function useRefreshFeeds() {
    const queryClient = useQueryClient()
    const refreshFeed = useRefreshFeed()
    const [isRefreshing, setIsRefreshing] = useState(false)
    const inFlightRef = useRef(false)

    const refreshFeeds = useCallback(
        async (feedId?: string) => {
            if (inFlightRef.current) return
            inFlightRef.current = true
            setIsRefreshing(true)

            try {
                if (feedId) {
                    try {
                        await refreshFeed.mutateAsync({
                            feedId,
                            forceRefetch: true,
                        })
                    } catch (error) {
                        // A 429 (the server's 60s per-feed cooldown) is expected when the
                        // reader pulls twice quickly. Still revalidate below.
                        console.error("Feed refresh failed:", error)
                    }
                }

                await Promise.all([
                    queryClient.invalidateQueries({
                        queryKey: [RSS_QUERY_KEYS.ARTICLES],
                        refetchType: "active",
                    }),
                    queryClient.invalidateQueries({
                        queryKey: queryKeys.unreadCounts(),
                        refetchType: "active",
                    }),
                    queryClient.invalidateQueries({
                        queryKey: [RSS_QUERY_KEYS.FEEDS, "list"],
                        refetchType: "active",
                    }),
                ])
            } catch (error) {
                console.error("Failed to refresh feeds:", error)
            } finally {
                inFlightRef.current = false
                setIsRefreshing(false)
            }
        },
        [queryClient, refreshFeed]
    )

    return { refreshFeeds, isRefreshing }
}
