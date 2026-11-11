import { useUpdateArticle, type Article } from "@infrss/shared"
import { useEffect, useState } from "react"
import { toast } from "react-hot-toast"

import { useArticlesStore } from "../stores/use-articles-store"
import { useAutoMarkRead } from "./use-auto-mark-read"

interface UseArticleInteractionsProps {
    article: Article
    isRecentlyReadMode: boolean
    isReadLaterMode: boolean
    isTodayMode?: boolean
    shouldShowPreviewBanner: boolean
    isMobile: boolean
    onMarkAsRead?: () => void
    onArticleRemoved?: () => void
}

export function useArticleInteractions({
    article,
    isRecentlyReadMode,
    isReadLaterMode,
    isTodayMode = false,
    shouldShowPreviewBanner,
    isMobile,
    onMarkAsRead,
    onArticleRemoved,
}: UseArticleInteractionsProps) {
    const [hasMarkedRead, setHasMarkedRead] = useState(false)
    const updateArticle = useUpdateArticle()
    const markReadQuietly = useAutoMarkRead()
    const addAutoReadIds = useArticlesStore((state) => state.addAutoReadIds)

    // Reset read state when article ID changes
    useEffect(() => {
        setHasMarkedRead(false)
    }, [article.id])

    const handleMarkAsRead = () => {
        // Allow if in read later mode (to unsave) or if not read yet
        if (hasMarkedRead || (article.is_read && !isReadLaterMode)) return

        setHasMarkedRead(true)
        if (onMarkAsRead) {
            onMarkAsRead()
            return
        }

        const updateData: { is_read: boolean; is_saved?: boolean } = {
            is_read: true,
        }

        updateArticle.mutate(
            {
                articleId: article.id,
                data: updateData,
                articleType: article.article_type,
            },
            {
                onSuccess: () => {
                    onArticleRemoved?.()
                },
                onError: () => {
                    setHasMarkedRead(false)
                },
            }
        )
    }

    const handleToggleReadLater = () => {
        const newReadLaterState = !article.is_saved

        updateArticle.mutate(
            {
                articleId: article.id,
                data: {
                    is_saved: newReadLaterState,
                },
                articleType: article.article_type,
            },
            {
                onError: () => {
                    toast.error("Failed to update read later status")
                },
            }
        )
    }

    /**
     * Implicit read-marking: scrolling the article, or clicking into its text.
     *
     * Deliberately bypasses `useUpdateArticle`, which cancels in-flight queries on mutate and
     * refetches every article list on settle. That refetch comes back with the server-side
     * unread filter applied, so the article being read drops out of the list, the split view
     * auto-selects a different one, and the reader loses its place mid-scroll. Quiet marking
     * patches the caches optimistically and PATCHes fire-and-forget instead. The id is also
     * pinned in `autoReadIds` so the unread-only list keeps the row (dimmed) instead of
     * shifting the list underneath the reader.
     */
    const handleQuietMarkAsRead = () => {
        if (hasMarkedRead || article.is_read) return

        setHasMarkedRead(true)
        addAutoReadIds([article.id])
        markReadQuietly(article, { affectsToday: isTodayMode })
    }

    const handleScrollMarkAsRead = (scrollTop: number) => {
        if (
            isRecentlyReadMode ||
            isReadLaterMode ||
            shouldShowPreviewBanner ||
            hasMarkedRead ||
            article.is_read ||
            isMobile
        )
            return

        // Mark as read on minimal scroll (just 50px) to be more responsive
        if (scrollTop > 50) {
            handleQuietMarkAsRead()
        }
    }

    const handleContentClickMarkAsRead = () => {
        // Mark as read on content click (desktop only, not in preview or read modes)
        if (
            !isRecentlyReadMode &&
            !isReadLaterMode &&
            !shouldShowPreviewBanner &&
            !article.is_read &&
            !isMobile
        ) {
            handleQuietMarkAsRead()
        }
    }

    // Use isPending to show optimistic state immediately while mutation is in flight
    // This serves as a fallback if the cache update hasn't propagated yet
    const optimisticReadLater =
        updateArticle.isPending &&
        updateArticle.variables?.articleId === article.id &&
        updateArticle.variables.data.is_saved !== undefined
            ? updateArticle.variables.data.is_saved
            : article.is_saved

    const optimisticIsRead =
        updateArticle.isPending &&
        updateArticle.variables?.articleId === article.id &&
        updateArticle.variables.data.is_read !== undefined
            ? updateArticle.variables.data.is_read
            : article.is_read

    return {
        hasMarkedRead,
        optimisticReadLater,
        optimisticIsRead,
        handleMarkAsRead,
        handleToggleReadLater,
        handleScrollMarkAsRead,
        handleContentClickMarkAsRead,
    }
}
