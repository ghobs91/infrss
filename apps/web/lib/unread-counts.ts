/**
 * Unread totals derived from the per-feed counts the API returns.
 *
 * `/api/articles/counts` has no server-side "all articles" aggregate, so the header, the sidebar
 * and the mobile dock all derive it the same way to keep their badges in agreement.
 */

/** Sum of every feed's unread count — the "All Articles" total. */
export function sumFeedUnreadCounts(
    feedCounts?: Record<string, number> | null
): number {
    if (!feedCounts) return 0
    return Object.values(feedCounts).reduce(
        (total, count) => total + (count || 0),
        0
    )
}
