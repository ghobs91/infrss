import NextImage from "next/image"
import { AlertTriangle, Check, CircleDashed } from "lucide-react"

import { FeedCardSkeleton } from "@/components/features/feeds/FeedCardSkeleton"
import { FeedPreviewCard } from "@/components/features/feeds/FeedPreviewCard"
import { Button } from "@/components/ui/button"
import {
    type ContentType,
    type FeedDiscoveryResult,
    type FeedDiscoveryStep,
    type FeedSummary,
} from "@infrss/shared"
import { cn } from "@/lib/utils"

interface UrlDiscoveryResultsProps {
    /** Feeds the backend found for the pasted URL */
    feeds: FeedDiscoveryResult[]
    /** Every strategy the backend tried, in order */
    steps: FeedDiscoveryStep[]
    /** Whether the pasted URL was itself a feed */
    isDirectFeed: boolean
    /** Whether discovery is still running */
    isLoading: boolean
    /** Error message when discovery failed */
    error: string | null
    /** Whether the request failed */
    isError: boolean
    /** Whether discovery finished without finding any feed */
    hasNoFeeds: boolean
    /** Callback to clear the search */
    onClearSearch: () => void
}

const STEP_STATUS_ICON = {
    ok: Check,
    failed: AlertTriangle,
    skipped: CircleDashed,
} as const

function stepStatusText(step: FeedDiscoveryStep): string {
    if (step.status === "skipped") return "Not needed"
    if (step.status === "failed") return "Could not check"
    return `Found ${step.found} ${step.found === 1 ? "feed" : "feeds"}`
}

/**
 * Checklist of the strategies the feed finder ran for a pasted URL.
 *
 * Mirrors the transparency of dedicated feed finders: every attempted search is listed with how
 * many feeds it turned up, so "no feeds found" is explainable instead of mysterious.
 */
function DiscoverySteps({ steps }: { steps: FeedDiscoveryStep[] }) {
    if (steps.length === 0) return null

    return (
        <ul className="space-y-1.5" aria-label="Feed discovery steps">
            {steps.map((step) => {
                const Icon = STEP_STATUS_ICON[step.status] ?? CircleDashed
                const isOk = step.status === "ok"
                return (
                    <li
                        key={step.key}
                        className="flex items-start gap-2 text-xs md:text-sm"
                    >
                        <Icon
                            aria-hidden="true"
                            className={cn(
                                "mt-0.5 h-3.5 w-3.5 shrink-0",
                                isOk
                                    ? "text-[#6A994E] dark:text-primary"
                                    : "text-muted-foreground/60"
                            )}
                        />
                        <span
                            className={cn(
                                isOk
                                    ? "font-medium text-foreground"
                                    : "text-muted-foreground"
                            )}
                        >
                            {step.label}:
                        </span>{" "}
                        <span className="text-muted-foreground">
                            {stepStatusText(step)}
                        </span>
                    </li>
                )
            })}
        </ul>
    )
}

/** Adapt a discovered feed into the shape the preview card renders. */
function createPreviewFeedData(
    previewFeed: FeedDiscoveryResult
): FeedSummary & { is_preview: true } {
    return {
        id: previewFeed.id ?? "",
        url: previewFeed.url ?? "",
        title: previewFeed.title,
        link: previewFeed.link ?? null,
        image_url: previewFeed.image_url ?? null,
        is_preview: true,
        is_subscribed: previewFeed.is_subscribed,
        language: previewFeed.language ?? "en",
        author: previewFeed.author ?? null,
        content_type: (previewFeed.content_type as ContentType) ?? null,
        tags: previewFeed.tags ?? [],
        tags_native: previewFeed.tags_native ?? [],
        description: previewFeed.description,
    }
}

function resultsHeading(
    feeds: FeedDiscoveryResult[],
    isDirectFeed: boolean
): string {
    if (isDirectFeed && feeds.length === 1) return "Feed Preview"
    if (feeds.length === 1) return "Feed found on this site"
    return `${feeds.length} feeds found on this site`
}

/**
 * Results for a URL pasted into Discover.
 *
 * The backend tries the URL as a feed and then walks a discovery ladder (page feed declarations,
 * parent pages, links, sitemap, common suffixes, blog hints, third-party hosts). Whatever it finds
 * is shown as subscribeable preview cards, with the searched strategies listed underneath.
 */
export function UrlDiscoveryResults({
    feeds,
    steps,
    isDirectFeed,
    isLoading,
    error,
    isError,
    hasNoFeeds,
    onClearSearch,
}: UrlDiscoveryResultsProps) {
    if (isLoading) {
        return (
            <div className="mb-8">
                <div className="flex items-center justify-between mb-2 pl-5 pr-2">
                    <h3 className="text-sm font-medium text-muted-foreground">
                        Searching this site for feeds…
                    </h3>
                </div>
                <FeedCardSkeleton />
            </div>
        )
    }

    if (isError) {
        return (
            <div className="flex flex-col items-center justify-center py-16">
                <h3 className="text-xl font-medium mb-3 text-foreground dark:text-foreground">
                    Could not search this site
                </h3>
                <p className="text-muted-foreground text-center max-w-md mb-6">
                    {error ||
                        "We couldn't search that URL for feeds. Please try again."}
                </p>
                <Button variant="outline" onClick={onClearSearch}>
                    Try again
                </Button>
            </div>
        )
    }

    if (hasNoFeeds || feeds.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <div className="mb-6">
                    <NextImage
                        src="/discover/Search.svg"
                        alt="No feeds found"
                        width={132}
                        height={128}
                        className="w-32 h-auto"
                    />
                </div>
                <h3 className="text-xl font-medium mb-3 text-foreground dark:text-foreground">
                    No feeds found on this site
                </h3>
                <p className="text-muted-foreground text-center max-w-md mb-6">
                    We checked the page, its parent pages, its links, the
                    sitemap and the common feed paths. Try a direct feed URL
                    instead.
                </p>
                {steps.length > 0 && (
                    <div className="w-full max-w-md rounded-lg border border-border/50 p-4">
                        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            What we searched
                        </p>
                        <DiscoverySteps steps={steps} />
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="mb-8">
            <div className="flex items-center justify-between mb-2 pl-5 pr-2">
                <h3 className="text-sm font-medium text-muted-foreground">
                    {resultsHeading(feeds, isDirectFeed)}
                </h3>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClearSearch}
                    className="h-7 px-2.5 text-xs text-muted-foreground hover:text-[#6A994E] hover:bg-[#F3F9EF] dark:hover:text-primary dark:hover:bg-accent rounded-md cursor-pointer transition-colors"
                >
                    Clear
                </Button>
            </div>

            <div className="space-y-3">
                {feeds.map((feed, index) => (
                    <FeedPreviewCard
                        key={`${feed.url ?? "feed"}-${index}`}
                        feed={createPreviewFeedData(feed)}
                    />
                ))}
            </div>

            {steps.length > 0 && (
                <details className="mt-4 pl-1">
                    <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors">
                        How we searched
                    </summary>
                    <div className="mt-2">
                        <DiscoverySteps steps={steps} />
                    </div>
                </details>
            )}
        </div>
    )
}
