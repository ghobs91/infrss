"use client"

import {
    ApiClient,
    queryKeys,
    RSS_QUERY_KEYS,
    type Article,
    type ArticleCountsResponse,
} from "@infrss/shared"
import { useQueryClient } from "@tanstack/react-query"
import { useCallback, useRef } from "react"

interface CachedArticlesPage {
    pages?: { items?: Article[] }[]
}

/**
 * Quiet read-marking for implicit reading gestures (scrolling past a row in the list, or
 * scrolling/clicking into the open reader).
 *
 * Deliberately does not reuse `useUpdateArticle`: its `onMutate` cancels in-flight article
 * queries (including an infinite-scroll page) and `onSettled` refetches every active list after
 * each mutation. That's right for a deliberate click on "mark as read", but during a scroll it
 * would cancel pagination and fire a refetch per row — and in the reader it drops the article
 * being read out of the server-side unread list, which makes the split view jump to another
 * article. Here the cache is patched optimistically and the PATCH is fire-and-forget; the next
 * natural refetch reconciles with the server.
 */
export function useAutoMarkRead() {
    const queryClient = useQueryClient()
    const queueRef = useRef<Article[]>([])
    const activeRef = useRef(0)

    return useCallback(
        (article: Article) => {
            if (article.is_read) return

            queryClient.setQueriesData<CachedArticlesPage>(
                { queryKey: [RSS_QUERY_KEYS.ARTICLES] },
                (oldData) => {
                    if (!oldData?.pages) return oldData
                    return {
                        ...oldData,
                        pages: oldData.pages.map((page) => ({
                            ...page,
                            items: page.items?.map((item) =>
                                item.id === article.id
                                    ? { ...item, is_read: true }
                                    : item
                            ),
                        })),
                    }
                }
            )

            queryClient.setQueryData<Article>(
                queryKeys.article(article.id),
                (old) => (old ? { ...old, is_read: true } : old)
            )

            const feedId = article.feed_id
            if (feedId) {
                queryClient.setQueryData<ArticleCountsResponse>(
                    queryKeys.unreadCounts(),
                    (old) => {
                        const current = old?.feed_counts[feedId]
                        if (!old || current === undefined || current <= 0) {
                            return old
                        }
                        return {
                            ...old,
                            feed_counts: {
                                ...old.feed_counts,
                                [feedId]: current - 1,
                            },
                        }
                    }
                )
            }

            // Keep a small concurrency window: a fast fling can pass dozens of articles at
            // once, and the backend should see a trickle rather than a burst.
            const MAX_CONCURRENT = 3
            queueRef.current.push(article)

            const drain = () => {
                while (
                    activeRef.current < MAX_CONCURRENT &&
                    queueRef.current.length > 0
                ) {
                    const next = queueRef.current.shift()
                    if (!next) return
                    activeRef.current += 1
                    void ApiClient.updateArticle(
                        next.id,
                        { is_read: true },
                        next.article_type
                    )
                        .catch((error) => {
                            console.error(
                                "Failed to auto-mark article as read:",
                                error
                            )
                        })
                        .finally(() => {
                            activeRef.current -= 1
                            drain()
                        })
                }
            }

            drain()
        },
        [queryClient]
    )
}
