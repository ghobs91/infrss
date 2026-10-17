"use client"

import {
    type CatalogFeed,
    type CatalogSource,
    type FeedPreviewArticle,
    FEED_CATEGORIES,
    useCatalogSourcesQuery,
    usePreviewFeedUrl,
    useSubscribeCatalogFeedMutation,
} from "@infrss/shared"
import {
    ChevronDown,
    ExternalLink,
    FlaskConical,
    Landmark,
    MoreHorizontal,
    Plus,
    type LucideIcon,
} from "lucide-react"
import { useCallback, useMemo, useState } from "react"
import toast from "react-hot-toast"

import { FeedIcon } from "@/components/features/feeds/FeedIcon"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { CATEGORY_CONFIG } from "@/lib/categories"
import { cn } from "@/lib/utils"

interface SourceGroup {
    id: string
    label: string
    icon: LucideIcon
    sources: CatalogSource[]
}

interface GroupMeta {
    id: string
    label: string
    icon: LucideIcon
    order: number
}

/** Favicon for an organisation's own domain (same service the reader uses for clipped articles). */
function faviconUrl(domain: string): string {
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
}

function feedTypeLabel(type: CatalogFeed["feed_type"]): string {
    return type.replace(/_/g, " ").toLowerCase()
}

function formatPublished(value: string | null): string | null {
    if (!value) return null
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return null
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

function sectionDomId(groupId: string): string {
    return `primary-source-section-${groupId}`
}

/**
 * Decide which section a source belongs to. Company sources carry a topic `category`; government
 * and research entities usually do not, so they get dedicated sections derived from their type
 * rather than falling into "Miscellaneous".
 */
function groupMetaFor(source: CatalogSource): GroupMeta {
    if (source.category) {
        const config = CATEGORY_CONFIG[source.category]
        return {
            id: source.category,
            label: config?.name ?? source.category,
            icon: config?.icon ?? MoreHorizontal,
            order: 10 + FEED_CATEGORIES.indexOf(source.category),
        }
    }
    if (source.entity_type === "GOV_FEDERAL" || source.entity_type === "GOV_STATE") {
        return { id: "government", label: "Government", icon: Landmark, order: 0 }
    }
    if (source.entity_type === "RESEARCH_ACADEMIC") {
        return { id: "research", label: "Research", icon: FlaskConical, order: 1 }
    }
    return { id: "other", label: "Other sources", icon: MoreHorizontal, order: 1000 }
}

/** Group sources into ordered sections: government, research, then topic categories. */
function groupSources(sources: CatalogSource[]): SourceGroup[] {
    const groups = new Map<string, SourceGroup & { order: number }>()
    for (const source of sources) {
        const meta = groupMetaFor(source)
        const existing = groups.get(meta.id)
        if (existing) {
            existing.sources.push(source)
        } else {
            groups.set(meta.id, {
                id: meta.id,
                label: meta.label,
                icon: meta.icon,
                order: meta.order,
                sources: [source],
            })
        }
    }
    return [...groups.values()].sort((a, b) => a.order - b.order)
}

function formatUpdatedAgo(updatedAt: number): string {
    if (!updatedAt) return "just now"
    const seconds = Math.max(0, Math.round((Date.now() - updatedAt) / 1000))
    if (seconds < 45) return "just now"
    const minutes = Math.round(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    return `${Math.round(minutes / 60)}h ago`
}

/**
 * The primary-source catalog, embedded under the Discover search bar. Every known source with at
 * least one verified feed, grouped into collapsible categories, with a sticky table of contents
 * for jumping between them. The list refreshes while the page is open. Clicking a source opens a
 * feed preview; the plus button subscribes (promotes the feed into the user's library).
 */
export function PrimarySourcesCatalog() {
    const sourcesQuery = useCatalogSourcesQuery()
    const sources = sourcesQuery.data ?? []
    const groups = useMemo(() => groupSources(sources), [sources])
    const subscribeMutation = useSubscribeCatalogFeedMutation()
    const [activeSource, setActiveSource] = useState<CatalogSource | null>(null)
    const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set())

    const toggleSection = useCallback((groupId: string) => {
        setCollapsed((previous) => {
            const next = new Set(previous)
            if (next.has(groupId)) {
                next.delete(groupId)
            } else {
                next.add(groupId)
            }
            return next
        })
    }, [])

    const jumpToSection = useCallback((groupId: string) => {
        const element = document.getElementById(sectionDomId(groupId))
        element?.scrollIntoView({ behavior: "smooth", block: "start" })
    }, [])

    function handleSubscribe(feedId: string) {
        toast.promise(subscribeMutation.mutateAsync({ feedId }), {
            loading: "Subscribing…",
            success: "Subscribed",
            error: "Could not subscribe",
        })
    }

    const subscribingFeedId = subscribeMutation.isPending
        ? subscribeMutation.variables?.feedId
        : undefined
    const feedCount = sources.reduce((total, source) => total + source.feeds.length, 0)

    return (
        <section className="w-full space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="space-y-1">
                    <h2 className="text-lg font-semibold tracking-tight">
                        Primary sources
                    </h2>
                    <p className="max-w-2xl text-sm text-muted-foreground">
                        Straight from the organisations that publish them —
                        government agencies, companies and research
                        institutions. Newly verified sources appear here
                        automatically; subscribe to add one to your library.
                    </p>
                </div>
                <LiveStatus
                    count={sources.length}
                    feedCount={feedCount}
                    updatedAt={sourcesQuery.dataUpdatedAt}
                    isFetching={sourcesQuery.isFetching}
                />
            </div>

            {sourcesQuery.isLoading ? (
                <CatalogSkeleton />
            ) : sourcesQuery.isError ? (
                <p className="text-sm text-muted-foreground">
                    Could not load the catalog. It will retry shortly.
                </p>
            ) : groups.length === 0 ? (
                <EmptyState />
            ) : (
                <div className="grid gap-6 lg:grid-cols-[190px_minmax(0,1fr)]">
                    {/* Table of contents — jump links to each category. */}
                    <nav
                        aria-label="Primary source categories"
                        className="hidden lg:block"
                    >
                        <div className="sticky top-4 space-y-0.5">
                            <p className="px-3 pb-1 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase">
                                Jump to
                            </p>
                            {groups.map((group) => (
                                <TocItem
                                    key={group.id}
                                    group={group}
                                    onClick={jumpToSection}
                                />
                            ))}
                        </div>
                    </nav>

                    <div className="min-w-0 space-y-6">
                        {groups.map((group) => (
                            <SourceCategorySection
                                key={group.id}
                                group={group}
                                collapsed={collapsed.has(group.id)}
                                onToggle={toggleSection}
                                onSubscribe={handleSubscribe}
                                onSelect={setActiveSource}
                                subscribingFeedId={subscribingFeedId}
                            />
                        ))}
                    </div>
                </div>
            )}

            <SourcePreviewDialog
                source={activeSource}
                onClose={() => setActiveSource(null)}
            />
        </section>
    )
}

function TocItem({
    group,
    onClick,
}: {
    group: SourceGroup
    onClick: (groupId: string) => void
}) {
    const Icon = group.icon
    return (
        <button
            type="button"
            onClick={() => onClick(group.id)}
            className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{group.label}</span>
            <span className="ml-auto text-xs tabular-nums">
                {group.sources.length}
            </span>
        </button>
    )
}

function LiveStatus({
    count,
    feedCount,
    updatedAt,
    isFetching,
}: {
    count: number
    feedCount: number
    updatedAt: number
    isFetching: boolean
}) {
    return (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span>
                {count} {count === 1 ? "source" : "sources"} · {feedCount}{" "}
                {feedCount === 1 ? "feed" : "feeds"} · updated{" "}
                {isFetching && !updatedAt ? "…" : formatUpdatedAgo(updatedAt)}
            </span>
        </div>
    )
}

function SourceCategorySection({
    group,
    collapsed,
    onToggle,
    onSubscribe,
    onSelect,
    subscribingFeedId,
}: {
    group: SourceGroup
    collapsed: boolean
    onToggle: (groupId: string) => void
    onSubscribe: (feedId: string) => void
    onSelect: (source: CatalogSource) => void
    subscribingFeedId?: string
}) {
    const Icon = group.icon

    return (
        <section id={sectionDomId(group.id)} className="scroll-mt-6 space-y-3">
            <button
                type="button"
                onClick={() => onToggle(group.id)}
                aria-expanded={!collapsed}
                className="flex w-full items-center gap-2 border-b border-border/60 pb-2 text-left"
            >
                <Icon className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold tracking-wide text-foreground">
                    {group.label}
                </h3>
                <span className="text-xs text-muted-foreground">
                    {group.sources.length}
                </span>
                <ChevronDown
                    className={cn(
                        "ml-auto h-4 w-4 text-muted-foreground transition-transform",
                        collapsed && "-rotate-90"
                    )}
                />
            </button>

            {!collapsed && (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {group.sources.map((source) => (
                        <SourceCard
                            key={source.id}
                            source={source}
                            onSubscribe={onSubscribe}
                            onSelect={onSelect}
                            subscribingFeedId={subscribingFeedId}
                        />
                    ))}
                </div>
            )}
        </section>
    )
}

function SourceCard({
    source,
    onSubscribe,
    onSelect,
    subscribingFeedId,
}: {
    source: CatalogSource
    onSubscribe: (feedId: string) => void
    onSelect: (source: CatalogSource) => void
    subscribingFeedId?: string
}) {
    return (
        <Card
            role="button"
            tabIndex={0}
            aria-label={`Preview ${source.name}`}
            onClick={() => onSelect(source)}
            onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault()
                    onSelect(source)
                }
            }}
            className="flex h-full cursor-pointer flex-col border bg-card/50 shadow-sm transition-colors hover:bg-accent/40 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
            <CardContent className="flex flex-1 flex-col gap-3 p-4">
                <div className="flex items-start gap-3">
                    <FeedIcon
                        feed={{
                            title: source.name,
                            image_url: faviconUrl(source.canonical_domain),
                        }}
                        className="mt-0.5 h-8 w-8 shrink-0 rounded"
                    />
                    <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-foreground">
                            {source.name}
                        </p>
                        <a
                            href={`https://${source.canonical_domain}`}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(event) => event.stopPropagation()}
                            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                        >
                            {source.canonical_domain}
                            <ExternalLink className="h-3 w-3" />
                        </a>
                    </div>
                </div>

                <div className="mt-auto space-y-2">
                    {source.feeds.map((feed) => (
                        <div
                            key={feed.id}
                            className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-background/40 px-3 py-2"
                        >
                            <div className="min-w-0 space-y-0.5">
                                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                    {feedTypeLabel(feed.feed_type)}
                                </p>
                                <p
                                    className="truncate text-[11px] text-muted-foreground"
                                    title={feed.feed_url}
                                >
                                    {feed.feed_url}
                                </p>
                            </div>
                            <Button
                                size="icon"
                                variant="secondary"
                                aria-label={`Subscribe to ${source.name}`}
                                disabled={subscribingFeedId === feed.id}
                                onClick={(event) => {
                                    event.stopPropagation()
                                    onSubscribe(feed.id)
                                }}
                                className="h-7 w-7 shrink-0 rounded-full"
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}

function SourcePreviewDialog({
    source,
    onClose,
}: {
    source: CatalogSource | null
    onClose: () => void
}) {
    return (
        <Dialog open={!!source} onOpenChange={(open) => !open && onClose()}>
            {source && (
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-3">
                            <FeedIcon
                                feed={{
                                    title: source.name,
                                    image_url: faviconUrl(source.canonical_domain),
                                }}
                                className="h-8 w-8 shrink-0 rounded"
                            />
                            <span className="truncate">{source.name}</span>
                        </DialogTitle>
                        <DialogDescription>
                            {source.canonical_domain} · {source.feeds.length}{" "}
                            {source.feeds.length === 1 ? "verified feed" : "verified feeds"}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="max-h-[65vh] space-y-4 overflow-y-auto pr-1">
                        {source.feeds.map((feed) => (
                            <FeedPreviewSection key={feed.id} feed={feed} />
                        ))}
                    </div>
                </DialogContent>
            )}
        </Dialog>
    )
}

function FeedPreviewSection({ feed }: { feed: CatalogFeed }) {
    const preview = usePreviewFeedUrl(feed.feed_url)
    const items: FeedPreviewArticle[] = preview.data?.articles ?? []

    return (
        <div className="space-y-3 rounded-lg border p-4">
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                {feedTypeLabel(feed.feed_type)}
            </p>

            {preview.isLoading ? (
                <div className="space-y-2">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-5/6" />
                </div>
            ) : preview.isError ? (
                <p className="text-xs text-muted-foreground">
                    Couldn&apos;t load a preview for this feed.{" "}
                    <a
                        href={feed.feed_url}
                        target="_blank"
                        rel="noreferrer"
                        className="underline underline-offset-2 hover:text-foreground"
                    >
                        Open the feed
                    </a>
                    .
                </p>
            ) : (
                <>
                    {preview.data?.title && (
                        <p className="text-sm font-medium text-foreground">
                            {preview.data.title}
                        </p>
                    )}
                    {preview.data?.description && (
                        <p className="line-clamp-3 text-xs text-muted-foreground">
                            {preview.data.description}
                        </p>
                    )}
                    {items.length === 0 ? (
                        <p className="text-xs text-muted-foreground">
                            No recent items in this feed.
                        </p>
                    ) : (
                        <ul className="divide-y divide-border/60">
                            {items.slice(0, 8).map((item, index) => {
                                const published = formatPublished(item.published_at)
                                return (
                                    <li key={index} className="py-2">
                                        <a
                                            href={item.link}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="text-sm text-foreground hover:underline"
                                        >
                                            {item.title || item.link}
                                        </a>
                                        {published && (
                                            <p className="text-[11px] text-muted-foreground">
                                                {published}
                                            </p>
                                        )}
                                    </li>
                                )
                            })}
                        </ul>
                    )}
                </>
            )}
        </div>
    )
}

function CatalogSkeleton() {
    return (
        <div className="grid gap-6 lg:grid-cols-[190px_minmax(0,1fr)]">
            <div className="hidden space-y-1 lg:block">
                {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-7 w-full" />
                ))}
            </div>
            <div className="space-y-6">
                {Array.from({ length: 2 }).map((_, sectionIndex) => (
                    <div key={sectionIndex} className="space-y-3">
                        <Skeleton className="h-5 w-40" />
                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                            {Array.from({ length: 3 }).map((_, cardIndex) => (
                                <Skeleton key={cardIndex} className="h-32 w-full" />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

function EmptyState() {
    return (
        <div className="rounded-lg border border-dashed border-border/60 px-6 py-12 text-center">
            <p className="text-sm font-medium text-foreground">
                No verified sources yet
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
                We&apos;re continuously discovering and verifying agency,
                company and research feeds. Check back soon.
            </p>
        </div>
    )
}
