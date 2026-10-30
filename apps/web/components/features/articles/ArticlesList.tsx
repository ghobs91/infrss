"use client"

import { useEffect, useRef, type UIEvent } from "react"
import { Article, ArticleFilterMode } from "@infrss/shared"
import { CalendarIcon } from "lucide-react"
import { ArticleItem } from "./ArticleItem"
import { ArticlesEmptyState } from "./ArticlesEmptyState"
import { ArticlesViewSkeleton } from "./ArticlesViewSkeleton"
import { useArticleGrouping } from "./hooks/use-article-grouping"
import { useArticleVirtualizer } from "./hooks/use-article-virtualizer"
import { useAutoMarkRead } from "./hooks/use-auto-mark-read"
import { useArticlesStore } from "./stores/use-articles-store"
import { PullToRefresh } from "@/components/ui/pull-to-refresh"
import { useIsMobile } from "@/hooks/use-mobile"

interface ArticlesListProps {
    articles: Article[]
    selectedArticleId: string | null
    isLoading: boolean
    isFetchingNextPage: boolean
    hasNextPage: boolean
    showUnreadOnly: boolean
    isRecentlyReadMode?: boolean
    isReadLaterMode?: boolean
    isTodayMode?: boolean
    feedId?: string
    folderId?: string
    fetchNextPage: () => void
    onArticleSelect: (articleId: string) => void
    /** Manual refresh (mobile pull-to-refresh). */
    onRefresh: () => void | Promise<void>
}

/**
 * ArticlesList component handles the rendering and infinite scroll behavior
 * for the articles list view.
 */
export function ArticlesList({
    articles,
    selectedArticleId,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    showUnreadOnly,
    isRecentlyReadMode = false,
    isReadLaterMode = false,
    isTodayMode = false,
    feedId,
    folderId,
    fetchNextPage,
    onArticleSelect,
    onRefresh,
}: ArticlesListProps) {
    const isMobile = useIsMobile()

    // Auto-mark-read-on-scroll. Read later/recently read have no unread concept. In the
    // unread-only filter the row is kept visible (dimmed) via the store's autoReadIds so it
    // doesn't vanish mid-scroll and shift every row below it.
    const autoMarkEnabled = !isReadLaterMode && !isRecentlyReadMode
    const autoMarkedIdsRef = useRef<Set<string>>(new Set())
    const scrollBaselineRef = useRef<number | null>(null)
    const lastScrollCheckRef = useRef(0)
    const markRead = useAutoMarkRead()
    const addAutoReadIds = useArticlesStore((state) => state.addAutoReadIds)
    const clearAutoReadIds = useArticlesStore((state) => state.clearAutoReadIds)

    useEffect(() => {
        autoMarkedIdsRef.current.clear()
        scrollBaselineRef.current = null
    }, [feedId, folderId, isReadLaterMode, isRecentlyReadMode, showUnreadOnly])

    // Navigating away ends the session-scoped "keep auto-read rows visible" window.
    useEffect(() => () => clearAutoReadIds(), [clearAutoReadIds])
    // Group articles by date
    const { filteredArticles, allRows } = useArticleGrouping({
        articles,
        showUnreadOnly,
        isRecentlyReadMode,
        isReadLaterMode,
        isTodayMode,
    })

    // Virtualization logic
    const { parentRef, rowVirtualizer, isSticky, isActiveSticky } =
        useArticleVirtualizer({
            allRows,
            hasNextPage,
            isFetchingNextPage,
            fetchNextPage,
            isRecentlyReadMode,
            isTodayMode,
        })

    /**
     * Mark every article that has scrolled fully above the viewport as read.
     *
     * The virtualizer only renders the current window (+overscan), so a fast fling can skip
     * rows entirely. Working from the first *not yet passed* virtual row instead of the
     * rendered rows marks the correct contiguous range even when intermediate rows were never
     * mounted. A baseline on the first scroll event avoids marking a restored scroll position
     * as read on load.
     */
    const handleListScroll = (event: UIEvent<HTMLDivElement>) => {
        if (!autoMarkEnabled) return

        const scrollTop = event.currentTarget.scrollTop
        if (scrollBaselineRef.current === null) {
            scrollBaselineRef.current = scrollTop
            return
        }
        if (scrollTop <= scrollBaselineRef.current) return

        const now = Date.now()
        if (now - lastScrollCheckRef.current < 180) return
        lastScrollCheckRef.current = now

        const firstNotPassed = rowVirtualizer
            .getVirtualItems()
            .find((item) => item.end > scrollTop)
        if (!firstNotPassed) return

        for (let index = 0; index < firstNotPassed.index; index++) {
            const row = allRows[index]
            if (!row || "type" in row || row.is_read) continue
            if (autoMarkedIdsRef.current.has(row.id)) continue

            autoMarkedIdsRef.current.add(row.id)
            addAutoReadIds([row.id])
            markRead(row, { affectsToday: isTodayMode })
        }
    }

    // Scroll selected article into view — only when the *selection* changes,
    // not when `allRows` grows. `useArticleGrouping` returns a brand-new array
    // on every `fetchNextPage()` append; without this guard the effect re-fires
    // on each page load and yanks the scroll position back up to the selected
    // (usually first) article. The ref records the last id we scrolled to so
    // pagination is a no-op while clicks / keyboard nav still scroll.
    const lastScrolledIdRef = useRef<string | null>(null)
    useEffect(() => {
        if (!selectedArticleId) return
        if (selectedArticleId === lastScrolledIdRef.current) return
        const index = allRows.findIndex(
            (row) => row && !("type" in row) && row.id === selectedArticleId
        )
        if (index !== -1) {
            lastScrolledIdRef.current = selectedArticleId
            rowVirtualizer.scrollToIndex(index, { align: "auto" })
        }
    }, [selectedArticleId, allRows, rowVirtualizer])

    // Show loading skeleton while initial load
    if (isLoading) {
        return <ArticlesViewSkeleton />
    }

    // Show empty state when no articles
    if (filteredArticles.length === 0) {
        return (
            <ArticlesEmptyState
                mode={
                    isRecentlyReadMode
                        ? ArticleFilterMode.RecentlyRead
                        : isReadLaterMode
                          ? ArticleFilterMode.ReadLater
                          : isTodayMode
                            ? ArticleFilterMode.Today
                            : ArticleFilterMode.AllArticles
                }
                feedId={feedId}
                folderId={folderId}
            />
        )
    }

    return (
        <PullToRefresh
            scrollRef={parentRef}
            onRefresh={onRefresh}
            enabled={isMobile}
        >
            <div
                ref={parentRef}
                className="h-full w-full overflow-auto scroll-smooth overscroll-contain max-md:mobile-dock-pb"
                style={{ scrollbarGutter: "stable" }}
                onScroll={handleListScroll}
            >
                <div
                    style={{
                        height: `${rowVirtualizer.getTotalSize()}px`,
                        width: "100%",
                        position: "relative",
                    }}
                >
                    {rowVirtualizer.getVirtualItems().map((virtualItem) => {
                        const item = allRows[virtualItem.index]
                        const isLoaderRow =
                            virtualItem.index > allRows.length - 1
                        const isStickyItem = isSticky(virtualItem.index)
                        const isActiveStickyItem = isActiveSticky(
                            virtualItem.index
                        )

                        // Check if this is the last article item before a header or end
                        const nextItem = allRows[virtualItem.index + 1]
                        const isLastArticleInGroup =
                            item &&
                            !("type" in item) &&
                            (!nextItem ||
                                ("type" in nextItem &&
                                    nextItem.type === "header"))

                        return (
                            <div
                                key={virtualItem.index}
                                data-index={virtualItem.index}
                                ref={rowVirtualizer.measureElement}
                                style={{
                                    ...(isStickyItem && isActiveStickyItem
                                        ? {
                                              background: "var(--background)",
                                              zIndex: 10,
                                          }
                                        : {}),
                                    ...(isActiveStickyItem
                                        ? {
                                              position: "sticky",
                                          }
                                        : {
                                              position: "absolute",
                                              transform: `translateY(${virtualItem.start}px)`,
                                          }),
                                    top: 0,
                                    left: 0,
                                    width: "100%",
                                }}
                            >
                                {isLoaderRow ? (
                                    // Loading indicator
                                    hasNextPage && isFetchingNextPage ? (
                                        <div className="flex justify-center py-4">
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                                                Loading more articles...
                                            </div>
                                        </div>
                                    ) : null
                                ) : item ? (
                                    <>
                                        {"type" in item &&
                                        item.type === "header" ? (
                                            // Date Header with reasonable 48px height
                                            <div
                                                className={`flex items-center gap-2 px-4 py-2 bg-background/95 backdrop-blur-sm ${isActiveStickyItem ? "border-b" : ""}`}
                                            >
                                                <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                                                <h3 className="text-sm font-medium text-muted-foreground">
                                                    {item.label}
                                                </h3>
                                            </div>
                                        ) : (
                                            <ArticleItem
                                                key={(item as Article).id}
                                                article={item as Article}
                                                isActive={
                                                    selectedArticleId ===
                                                    (item as Article).id
                                                }
                                                isLastInGroup={
                                                    isLastArticleInGroup
                                                }
                                                isRecentlyReadMode={
                                                    isRecentlyReadMode
                                                }
                                                isReadLaterMode={
                                                    isReadLaterMode
                                                }
                                                onClick={() =>
                                                    onArticleSelect(
                                                        (item as Article).id
                                                    )
                                                }
                                            />
                                        )}
                                    </>
                                ) : null}
                            </div>
                        )
                    })}
                </div>
            </div>
        </PullToRefresh>
    )
}
