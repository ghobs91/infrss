import {
    type FeedDiscoveryReport,
    type FeedDiscoveryStep,
    type FeedDiscoveryResult,
    useFindFeeds,
} from "@infrss/shared"
import { useMemo } from "react"
import { useDebounce } from "@/hooks/use-debounce"

/** Typing an address produces a URL at every keystroke, so wait before crawling the site. */
const URL_DISCOVERY_DEBOUNCE_MS = 700

/**
 * Detect if a string is a URL pattern (http://, https://, rsshub://)
 */
function isUrl(str: string): boolean {
    const urlPattern = /^(https?:\/\/|rsshub:\/\/)/i
    return urlPattern.test(str.trim())
}

interface UseFeedDiscoveryResult {
    /** Feeds found for the URL, empty while searching or when the site publishes none */
    feeds: FeedDiscoveryResult[]
    /** Every strategy the backend tried, in order */
    steps: FeedDiscoveryStep[]
    /** Whether the entered URL was itself a feed */
    isDirectFeed: boolean
    /** Whether a discovery request is in flight (including the typing debounce) */
    isLoading: boolean
    /** Error message if discovery failed */
    error: string | null
    /** Whether the query is a URL */
    isUrlQuery: boolean
    /** Whether the query has failed */
    isError: boolean
    /** Whether discovery finished without finding any feed */
    hasNoFeeds: boolean
}

function errorMessage(error: Error | null): string | null {
    if (!error) return null
    if (error.message) return error.message
    return "Could not search this site for feeds"
}

/**
 * Hook for detecting URLs in search queries and finding the feeds a site publishes.
 *
 * When a user pastes a website URL into the search box, this hook:
 * 1. Detects if the query is a URL pattern
 * 2. Asks the backend to find feeds on that URL (or domain)
 * 3. Returns the discovered feeds plus the strategies that were tried
 */
export function useFeedDiscovery(query: string): UseFeedDiscoveryResult {
    const isUrlQuery = useMemo(() => isUrl(query), [query])
    const trimmedQuery = query.trim()
    const debouncedQuery = useDebounce(trimmedQuery, URL_DISCOVERY_DEBOUNCE_MS)

    const isDebouncing =
        isUrlQuery && trimmedQuery.length > 0 && debouncedQuery !== trimmedQuery

    const { data, isLoading, error, isError } = useFindFeeds(debouncedQuery, {
        enabled: isUrlQuery && debouncedQuery.length > 0,
    })

    const report: FeedDiscoveryReport | undefined = data

    return {
        feeds: report?.feeds ?? [],
        steps: report?.steps ?? [],
        isDirectFeed: report?.is_direct_feed ?? false,
        isLoading: isDebouncing || isLoading,
        error: errorMessage(error),
        isUrlQuery,
        isError,
        hasNoFeeds: Boolean(report) && (report?.feeds.length ?? 0) === 0,
    }
}
