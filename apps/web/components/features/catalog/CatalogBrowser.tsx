"use client"

import {
    type CatalogFeed,
    type VerificationStatus,
    useCatalogEntitiesQuery,
    useCatalogFeedsQuery,
    useSubscribeCatalogFeedMutation,
} from "@infrss/shared"
import { Landmark, Plus } from "lucide-react"
import { useState } from "react"
import toast from "react-hot-toast"

import { PrimarySourceBadge } from "@/components/features/articles/PrimarySourceBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

const STATUS_VARIANT: Record<
    VerificationStatus,
    {
        label: string
        variant: "success" | "secondary" | "destructive" | "outline"
    }
> = {
    VERIFIED_PRIMARY: { label: "Verified primary", variant: "success" },
    PENDING: { label: "Pending", variant: "secondary" },
    REJECTED_AGGREGATOR: {
        label: "Rejected (aggregator)",
        variant: "destructive",
    },
    QUARANTINED: { label: "Quarantined", variant: "outline" },
}

/**
 * Browse the primary-source catalog: pick an entity on the left, see its candidate feeds on the
 * right. Subscribing promotes a verified feed into the user's library.
 */
export function CatalogBrowser() {
    const entitiesQuery = useCatalogEntitiesQuery({ limit: 100 })
    const entities = entitiesQuery.data ?? []
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const activeId = selectedId ?? entities[0]?.id ?? null

    const feedsQuery = useCatalogFeedsQuery(activeId)
    const feeds = feedsQuery.data ?? []
    const subscribeMutation = useSubscribeCatalogFeedMutation()

    function handleSubscribe(feedId: string) {
        toast.promise(subscribeMutation.mutateAsync({ feedId }), {
            loading: "Subscribing…",
            success: "Subscribed",
            error: "Could not subscribe",
        })
    }

    return (
        <div className="mx-auto w-full max-w-6xl px-4 py-8">
            <header className="mb-6 space-y-1">
                <h1 className="text-2xl font-bold tracking-tight">
                    Primary source catalog
                </h1>
                <p className="text-sm text-muted-foreground">
                    Verified government, corporate and research sources.
                    Subscribing adds a feed to your library.
                </p>
            </header>

            <div className="grid gap-6 md:grid-cols-[280px_1fr]">
                <aside className="space-y-1">
                    {entitiesQuery.isLoading ? (
                        <div className="space-y-2">
                            {Array.from({ length: 6 }).map((_, index) => (
                                <Skeleton key={index} className="h-10 w-full" />
                            ))}
                        </div>
                    ) : entities.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                            No entities catalogued yet.
                        </p>
                    ) : (
                        entities.map((entity) => (
                            <button
                                key={entity.id}
                                type="button"
                                onClick={() => setSelectedId(entity.id)}
                                className={cn(
                                    "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
                                    entity.id === activeId
                                        ? "bg-accent font-medium text-foreground"
                                        : "text-muted-foreground hover:bg-muted"
                                )}
                            >
                                <Landmark className="h-4 w-4 shrink-0" />
                                <span className="truncate">{entity.name}</span>
                            </button>
                        ))
                    )}
                </aside>

                <section className="space-y-3">
                    {feedsQuery.isLoading && activeId ? (
                        Array.from({ length: 3 }).map((_, index) => (
                            <Skeleton key={index} className="h-24 w-full" />
                        ))
                    ) : feeds.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                            {activeId
                                ? "No feeds catalogued for this entity yet."
                                : "Select an entity to see its feeds."}
                        </p>
                    ) : (
                        feeds.map((feed) => (
                            <CatalogFeedRow
                                key={feed.id}
                                feed={feed}
                                onSubscribe={handleSubscribe}
                                isSubscribing={
                                    subscribeMutation.isPending &&
                                    subscribeMutation.variables?.feedId ===
                                        feed.id
                                }
                            />
                        ))
                    )}
                </section>
            </div>
        </div>
    )
}

function CatalogFeedRow({
    feed,
    onSubscribe,
    isSubscribing,
}: {
    feed: CatalogFeed
    onSubscribe: (feedId: string) => void
    isSubscribing: boolean
}) {
    const status = STATUS_VARIANT[feed.verification_status]
    const canSubscribe = feed.verification_status !== "REJECTED_AGGREGATOR"

    return (
        <Card className="border bg-card/50 shadow-sm">
            <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="min-w-0 space-y-1">
                    <p className="truncate text-sm font-medium text-foreground">
                        {feed.feed_url}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                        {feed.verification_status === "VERIFIED_PRIMARY" ? (
                            <PrimarySourceBadge />
                        ) : (
                            <Badge variant={status.variant}>
                                {status.label}
                            </Badge>
                        )}
                        <span className="text-[11px] text-muted-foreground">
                            {feed.feed_type.replace(/_/g, " ").toLowerCase()}
                        </span>
                    </div>
                </div>
                <Button
                    size="sm"
                    variant="secondary"
                    className="shrink-0 gap-1"
                    disabled={!canSubscribe || isSubscribing}
                    onClick={() => onSubscribe(feed.id)}
                >
                    <Plus className="h-3.5 w-3.5" />
                    {isSubscribing ? "Subscribing…" : "Subscribe"}
                </Button>
            </CardContent>
        </Card>
    )
}
