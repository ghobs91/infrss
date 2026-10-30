"use client"

import {
    type CatalogFeed,
    type CatalogSource,
    type FeedPreviewArticle,
    useCatalogSourcesQuery,
    usePreviewFeedUrl,
    useProfile,
    useUpdateProfile,
} from "@infrss/shared"
import {
    Atom,
    Briefcase,
    Building2,
    Car,
    Check,
    ChevronDown,
    ChevronsLeft,
    ChevronsRight,
    Coins,
    ExternalLink,
    FlaskConical,
    Globe,
    GraduationCap,
    HardHat,
    HeartPulse,
    Home,
    Landmark,
    Leaf,
    Map as MapIcon,
    MapPin,
    MoreHorizontal,
    Plus,
    Scale,
    Shield,
    TrainFront,
    type LucideIcon,
} from "lucide-react"
import { type ReactNode, useCallback, useMemo, useState } from "react"
import toast from "react-hot-toast"

import { CatalogSubscribeDialog } from "@/components/features/catalog/CatalogSubscribeDialog"
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
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { usePersistentState } from "@/hooks/use-persistent-state"
import { CATEGORY_CONFIG } from "@/lib/categories"
import {
    GOVERNMENT_LEVEL_LABELS,
    type GovernmentLevel,
    governmentLevelFor,
    isGovernmentSource,
    sourceMatchesState,
} from "@/lib/government"
import { isValidZip, stateFromZip } from "@/lib/us-zip"
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
    return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
    })
}

function sectionDomId(groupId: string): string {
    return `primary-source-section-${groupId}`
}

/**
 * Government subcategories ("sectors"). The API stores a stable slug; labels and ordering live
 * here so the government section can grow without changing the schema again.
 */
const GOVERNMENT_SECTOR_LABELS: Record<string, string> = {
    transit: "Transit Agencies",
    transportation: "Transportation Departments",
    health: "Health & Human Services",
    commerce: "Commerce & Economic Development",
    finance: "Finance & Economy",
    science: "Science, Space & Energy",
    environment: "Environment, Agriculture & Lands",
    defense: "Defense & Veterans",
    justice: "Justice, Courts & Records",
    labor: "Labor & Workforce",
    housing: "Housing & Urban Development",
    education: "Education",
    international: "International Affairs",
    local: "State & Local Government",
    other: "Other Agencies",
}

const GOVERNMENT_SECTOR_ICONS: Record<string, LucideIcon> = {
    transit: TrainFront,
    transportation: Car,
    health: HeartPulse,
    commerce: Briefcase,
    finance: Coins,
    science: Atom,
    environment: Leaf,
    defense: Shield,
    justice: Scale,
    labor: HardHat,
    housing: Home,
    education: GraduationCap,
    international: Globe,
    local: Building2,
    other: MoreHorizontal,
}

interface GovernmentSectorGroup {
    sector: string
    label: string
    icon: LucideIcon
    sources: CatalogSource[]
}

const GOVERNMENT_LEVEL_ORDER: GovernmentLevel[] = [
    "federal",
    "state",
    "local",
    "international",
]

/**
 * Split the government section's sources into sectors. Sources with an unknown/missing sector
 * fall into "Other Agencies". Shared by the section body and the jump-to list so both agree on
 * labels, icons and alphabetical ordering.
 */
function governmentSectorGroups(
    sources: CatalogSource[]
): GovernmentSectorGroup[] {
    const grouped = new Map<string, CatalogSource[]>()
    for (const source of sources) {
        const key =
            source.sector && GOVERNMENT_SECTOR_LABELS[source.sector]
                ? source.sector
                : "other"
        const list = grouped.get(key)
        if (list) {
            list.push(source)
        } else {
            grouped.set(key, [source])
        }
    }

    return [...grouped.keys()]
        .map((sector) => ({
            sector,
            label:
                GOVERNMENT_SECTOR_LABELS[sector] ?? sector.replace(/_/g, " "),
            icon: GOVERNMENT_SECTOR_ICONS[sector] ?? MoreHorizontal,
            sources: grouped.get(sector) ?? [],
        }))
        .sort((a, b) => a.label.localeCompare(b.label))
}

function governmentLevelGroups(
    sources: CatalogSource[]
): Array<{ level: GovernmentLevel; sources: CatalogSource[] }> {
    const grouped = new Map<GovernmentLevel, CatalogSource[]>()
    for (const source of sources) {
        const level = governmentLevelFor(source)
        const list = grouped.get(level)
        if (list) {
            list.push(source)
        } else {
            grouped.set(level, [source])
        }
    }
    return GOVERNMENT_LEVEL_ORDER.filter((level) => grouped.has(level)).map(
        (level) => ({ level, sources: grouped.get(level) ?? [] })
    )
}

/**
 * Decide which section a source belongs to. Government entities get their own "My Government"
 * section regardless of topic category (it's a lens on government activity), split into sectors.
 * Everything else uses its topic category, then falls back to research/other by entity type.
 */
function groupMetaFor(source: CatalogSource): GroupMeta {
    if (isGovernmentSource(source)) {
        return {
            id: "government",
            label: "My Government",
            icon: Landmark,
        }
    }
    if (source.category) {
        const config = CATEGORY_CONFIG[source.category]
        return {
            id: source.category,
            label: config?.name ?? source.category,
            icon: config?.icon ?? MoreHorizontal,
        }
    }
    if (source.entity_type === "RESEARCH_ACADEMIC") {
        return {
            id: "research",
            label: "Research",
            icon: FlaskConical,
        }
    }
    return {
        id: "other",
        label: "Other sources",
        icon: MoreHorizontal,
    }
}

/**
 * Group sources into sections. My Government stays pinned as the primary lens; every other
 * section is sorted alphabetically by its display label.
 */
function groupSources(sources: CatalogSource[]): SourceGroup[] {
    const groups = new Map<string, SourceGroup>()
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
                sources: [source],
            })
        }
    }
    return [...groups.values()].sort((a, b) => {
        if (a.id === "government") return -1
        if (b.id === "government") return 1
        return a.label.localeCompare(b.label)
    })
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
    const { data: profile, isLoading: isProfileLoading } = useProfile()
    const updateProfile = useUpdateProfile()
    const [activeSource, setActiveSource] = useState<CatalogSource | null>(null)
    const [pendingSubscription, setPendingSubscription] = useState<{
        source: CatalogSource
        feed: CatalogFeed
    } | null>(null)
    const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set())
    const [editingZip, setEditingZip] = useState(false)
    const [isTocCollapsed, setTocCollapsed] = usePersistentState(
        "discover-toc-collapsed",
        false
    )
    const [showAllGovernment, setShowAllGovernment] = usePersistentState(
        "discover-government-show-all",
        false
    )

    const zipcode = profile?.government_zipcode ?? null
    const location = zipcode ? stateFromZip(zipcode) : null

    // Curated government view: federal sources plus state/local sources for the saved ZIP.
    // Without a ZIP (or when the user asks for the full list) every government source is shown.
    const visibleSources = useMemo(() => {
        if (!location || showAllGovernment) return sources
        return sources.filter((source) => {
            if (!isGovernmentSource(source)) return true
            if (governmentLevelFor(source) === "federal") return true
            return sourceMatchesState(source, location)
        })
    }, [sources, location, showAllGovernment])

    const totalGovernmentCount = useMemo(
        () => sources.filter(isGovernmentSource).length,
        [sources]
    )
    const groups = useMemo(() => {
        const result = groupSources(visibleSources)
        // Keep the section (and its ZIP controls) visible even when no state/local source
        // matches, so the user can change their location instead of losing the entry point.
        if (
            totalGovernmentCount > 0 &&
            !result.some((group) => group.id === "government")
        ) {
            result.unshift({
                id: "government",
                label: "My Government",
                icon: Landmark,
                sources: [],
            })
        }
        return result
    }, [visibleSources, totalGovernmentCount])
    const visibleGovernmentCount = useMemo(
        () => visibleSources.filter(isGovernmentSource).length,
        [visibleSources]
    )

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

    const handleSubscribe = useCallback(
        (source: CatalogSource, feed: CatalogFeed) => {
            setPendingSubscription({ source, feed })
        },
        []
    )

    const handleSaveZip = useCallback(
        async (nextZipcode: string) => {
            try {
                await updateProfile.mutateAsync({
                    government_zipcode: nextZipcode,
                })
                setShowAllGovernment(false)
                setEditingZip(false)
                toast.success("Government feeds updated")
            } catch {
                toast.error("Could not save your ZIP code")
            }
        },
        [setShowAllGovernment, updateProfile]
    )

    const feedCount = sources.reduce(
        (total, source) => total + source.feeds.length,
        0
    )

    return (
        <section className="w-full space-y-8">
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div className="space-y-2">
                    <h2 className="text-lg font-semibold tracking-tight">
                        Primary sources
                    </h2>
                    <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
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
                <div
                    className={cn(
                        "grid gap-8",
                        isTocCollapsed
                            ? "lg:grid-cols-[44px_minmax(0,1fr)]"
                            : "lg:grid-cols-[300px_minmax(0,1fr)]"
                    )}
                >
                    {/* Table of contents — collapsible jump links to each section. */}
                    <nav
                        aria-label="Primary source categories"
                        className="hidden lg:block"
                    >
                        {isTocCollapsed ? (
                            <div className="sticky top-6 flex justify-center">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-muted-foreground"
                                    aria-label="Show categories"
                                    title="Show categories"
                                    onClick={() => setTocCollapsed(false)}
                                >
                                    <ChevronsRight className="h-4 w-4" />
                                </Button>
                            </div>
                        ) : (
                            <div className="sticky top-6 space-y-1">
                                <div className="flex items-center justify-between px-3 pb-2">
                                    <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                                        Jump to
                                    </p>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        className="h-5 w-5 text-muted-foreground"
                                        aria-label="Hide categories"
                                        title="Hide categories"
                                        onClick={() => setTocCollapsed(true)}
                                    >
                                        <ChevronsLeft className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                                {groups.map((group) =>
                                    group.id === "government" ? (
                                        <GovernmentTocItem
                                            key={group.id}
                                            group={group}
                                            onClick={jumpToSection}
                                        />
                                    ) : (
                                        <TocItem
                                            key={group.id}
                                            group={group}
                                            onClick={jumpToSection}
                                        />
                                    )
                                )}
                            </div>
                        )}
                    </nav>

                    <div className="min-w-0 space-y-8">
                        {groups.map((group) => (
                            <SourceCategorySection
                                key={group.id}
                                group={group}
                                collapsed={collapsed.has(group.id)}
                                onToggle={toggleSection}
                                onSubscribe={handleSubscribe}
                                onSelect={setActiveSource}
                                governmentZipcode={zipcode}
                                governmentStateName={location?.name ?? null}
                                governmentControl={
                                    group.id === "government" ? (
                                        <GovernmentLocationPanel
                                            profileLoading={isProfileLoading}
                                            zipcode={zipcode}
                                            locationName={
                                                location?.name ?? null
                                            }
                                            editingZip={editingZip}
                                            onStartEditZip={() =>
                                                setEditingZip(true)
                                            }
                                            onCancelEditZip={() =>
                                                setEditingZip(false)
                                            }
                                            onSaveZip={handleSaveZip}
                                            isSavingZip={
                                                updateProfile.isPending
                                            }
                                            showAllGovernment={
                                                showAllGovernment
                                            }
                                            onToggleShowAll={() =>
                                                setShowAllGovernment(
                                                    (current) => !current
                                                )
                                            }
                                            visibleCount={
                                                visibleGovernmentCount
                                            }
                                            totalCount={totalGovernmentCount}
                                        />
                                    ) : undefined
                                }
                            />
                        ))}
                    </div>
                </div>
            )}

            <SourcePreviewDialog
                source={activeSource}
                onClose={() => setActiveSource(null)}
            />

            {pendingSubscription && (
                <CatalogSubscribeDialog
                    source={pendingSubscription.source}
                    feed={pendingSubscription.feed}
                    onClose={() => setPendingSubscription(null)}
                />
            )}
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
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="min-w-0 flex-1 leading-snug">{group.label}</span>
            <span className="ml-auto shrink-0 text-xs tabular-nums">
                {group.sources.length}
            </span>
        </button>
    )
}

/**
 * Jump-to entry for the government section: a collapsible parent whose children are the
 * government sectors, so a large section stays navigable.
 */
function GovernmentTocItem({
    group,
    onClick,
}: {
    group: SourceGroup
    onClick: (groupId: string) => void
}) {
    const Icon = group.icon
    const sectors = useMemo(
        () => governmentSectorGroups(group.sources),
        [group.sources]
    )
    const [open, setOpen] = useState(true)

    return (
        <div>
            <div className="flex items-center rounded-md text-sm text-muted-foreground">
                <button
                    type="button"
                    onClick={() => setOpen((value) => !value)}
                    aria-expanded={open}
                    aria-label={
                        open
                            ? "Collapse government subcategories"
                            : "Expand government subcategories"
                    }
                    className="rounded p-1 transition-colors hover:bg-muted hover:text-foreground"
                >
                    <ChevronDown
                        className={cn(
                            "h-3.5 w-3.5 transition-transform",
                            !open && "-rotate-90"
                        )}
                    />
                </button>
                <button
                    type="button"
                    onClick={() => onClick(group.id)}
                    className="flex flex-1 items-center gap-2 py-2 text-left transition-colors hover:text-foreground"
                >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="min-w-0 flex-1 leading-snug">
                        {group.label}
                    </span>
                    <span className="ml-auto shrink-0 text-xs tabular-nums">
                        {group.sources.length}
                    </span>
                </button>
            </div>

            {open && (
                <div className="mt-1 ml-3 space-y-1 border-l border-border/60 pl-2">
                    {sectors.map((sector) => {
                        const SectorIcon = sector.icon
                        return (
                            <button
                                key={sector.sector}
                                type="button"
                                onClick={() =>
                                    onClick(`government-${sector.sector}`)
                                }
                                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                            >
                                <SectorIcon className="h-3.5 w-3.5 shrink-0" />
                                <span className="min-w-0 flex-1 leading-snug">
                                    {sector.label}
                                </span>
                                <span className="ml-auto shrink-0 tabular-nums">
                                    {sector.sources.length}
                                </span>
                            </button>
                        )
                    })}
                </div>
            )}
        </div>
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
    governmentControl,
    governmentZipcode,
    governmentStateName,
}: {
    group: SourceGroup
    collapsed: boolean
    onToggle: (groupId: string) => void
    onSubscribe: (source: CatalogSource, feed: CatalogFeed) => void
    onSelect: (source: CatalogSource) => void
    governmentControl?: ReactNode
    governmentZipcode?: string | null
    governmentStateName?: string | null
}) {
    const Icon = group.icon

    return (
        <section id={sectionDomId(group.id)} className="scroll-mt-6 space-y-4">
            <button
                type="button"
                onClick={() => onToggle(group.id)}
                aria-expanded={!collapsed}
                className="flex w-full items-center gap-2 border-b border-border/60 pb-3 text-left"
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
                <>
                    {group.id === "government" && (
                        <>
                            {governmentControl}
                            <p className="-mt-1 text-xs text-muted-foreground">
                                Follow what federal, state and local agencies
                                are doing — transit, health, commerce,
                                transportation and more.
                            </p>
                        </>
                    )}
                    {group.id === "government" ? (
                        <GovernmentSourceGroups
                            sources={group.sources}
                            zipcode={governmentZipcode ?? null}
                            stateName={governmentStateName ?? null}
                            onSubscribe={onSubscribe}
                            onSelect={onSelect}
                        />
                    ) : (
                        <SourceGrid
                            sources={group.sources}
                            onSubscribe={onSubscribe}
                            onSelect={onSelect}
                        />
                    )}
                </>
            )}
        </section>
    )
}

function GovernmentLocationPanel({
    profileLoading,
    zipcode,
    locationName,
    editingZip,
    onStartEditZip,
    onCancelEditZip,
    onSaveZip,
    isSavingZip,
    showAllGovernment,
    onToggleShowAll,
    visibleCount,
    totalCount,
}: {
    profileLoading: boolean
    zipcode: string | null
    locationName: string | null
    editingZip: boolean
    onStartEditZip: () => void
    onCancelEditZip: () => void
    onSaveZip: (zipcode: string) => void
    isSavingZip: boolean
    showAllGovernment: boolean
    onToggleShowAll: () => void
    visibleCount: number
    totalCount: number
}) {
    if (profileLoading) {
        return <Skeleton className="h-16 w-full" />
    }

    if (!zipcode || editingZip) {
        return (
            <GovernmentZipSetup
                initialZipcode={zipcode ?? ""}
                isSaving={isSavingZip}
                onSave={onSaveZip}
                onCancel={zipcode ? onCancelEditZip : undefined}
            />
        )
    }

    const isCurated = !showAllGovernment
    const hiddenCount = totalCount - visibleCount

    return (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-border/60 bg-muted/30 px-4 py-3 text-xs text-muted-foreground">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span>
                {isCurated ? (
                    <>
                        Showing federal, {locationName ?? "state"} and local
                        feeds for{" "}
                    </>
                ) : (
                    <>Showing all government feeds · ZIP </>
                )}
                <span className="font-medium text-foreground">{zipcode}</span>
            </span>
            <Button
                type="button"
                variant="link"
                size="sm"
                className="h-auto p-0 text-xs"
                onClick={onStartEditZip}
            >
                Change
            </Button>
            {hiddenCount > 0 || showAllGovernment ? (
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="ml-auto h-7 text-xs"
                    onClick={onToggleShowAll}
                >
                    {showAllGovernment
                        ? "Show my government"
                        : `Show all ${totalCount} government feeds`}
                </Button>
            ) : null}
        </div>
    )
}

function GovernmentZipSetup({
    initialZipcode,
    isSaving,
    onSave,
    onCancel,
}: {
    initialZipcode: string
    isSaving: boolean
    onSave: (zipcode: string) => void
    onCancel?: () => void
}) {
    const [value, setValue] = useState(initialZipcode)
    const state = stateFromZip(value)
    const canSave = isValidZip(value) && !!state

    return (
        <div className="rounded-lg border border-border/60 bg-muted/30 p-5">
            <div className="flex items-start gap-4">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="space-y-1">
                    <p className="text-sm font-medium text-foreground">
                        Set up My Government
                    </p>
                    <p className="text-xs text-muted-foreground">
                        Enter your ZIP code and we&apos;ll curate federal,
                        state, and local feeds for your area.
                    </p>
                </div>
            </div>

            <form
                className="mt-4 flex flex-wrap items-center gap-3"
                onSubmit={(event) => {
                    event.preventDefault()
                    if (canSave && !isSaving) onSave(value.trim())
                }}
            >
                <Input
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    placeholder="ZIP code"
                    inputMode="numeric"
                    autoComplete="postal-code"
                    maxLength={10}
                    aria-label="ZIP code"
                    className="h-8 w-32"
                />
                <Button
                    type="submit"
                    size="sm"
                    className="h-8"
                    disabled={!canSave || isSaving}
                >
                    {isSaving ? "Saving…" : "Save"}
                </Button>
                {onCancel && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-8"
                        onClick={onCancel}
                    >
                        Cancel
                    </Button>
                )}
                {value.length >= 5 && !state && (
                    <p className="w-full text-xs text-destructive">
                        Enter a valid US ZIP code.
                    </p>
                )}
                {state && (
                    <p className="w-full text-xs text-muted-foreground">
                        {state.name}
                    </p>
                )}
            </form>
        </div>
    )
}

function SourceGrid({
    sources,
    onSubscribe,
    onSelect,
}: {
    sources: CatalogSource[]
    onSubscribe: (source: CatalogSource, feed: CatalogFeed) => void
    onSelect: (source: CatalogSource) => void
}) {
    return (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {sources.map((source) => (
                <SourceCard
                    key={source.id}
                    source={source}
                    onSubscribe={onSubscribe}
                    onSelect={onSelect}
                />
            ))}
        </div>
    )
}

/**
 * "My Government" is split by sector, then by level inside each sector, so the section stays
 * navigable and federal / state / local sources never mix in the same grid.
 */
function GovernmentSourceGroups({
    sources,
    zipcode,
    stateName,
    onSubscribe,
    onSelect,
}: {
    sources: CatalogSource[]
    zipcode: string | null
    stateName: string | null
    onSubscribe: (source: CatalogSource, feed: CatalogFeed) => void
    onSelect: (source: CatalogSource) => void
}) {
    const sectors = useMemo(() => governmentSectorGroups(sources), [sources])

    return (
        <div className="space-y-8">
            {sectors.map((sector) => {
                const SectorIcon = sector.icon
                const levels = governmentLevelGroups(sector.sources)
                return (
                    <section
                        key={sector.sector}
                        id={sectionDomId(`government-${sector.sector}`)}
                        className="scroll-mt-6 space-y-5 rounded-2xl border border-border/70 bg-muted/20 p-5 shadow-sm"
                    >
                        <div className="flex items-center gap-2">
                            <SectorIcon className="h-4 w-4 text-muted-foreground" />
                            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                                {sector.label}
                            </h4>
                            <span className="text-xs tabular-nums text-muted-foreground/70">
                                {sector.sources.length}
                            </span>
                        </div>
                        <div className="space-y-6">
                            {levels.map(({ level, sources: levelSources }) => (
                                <div key={level} className="space-y-3">
                                    <GovernmentLevelHeader
                                        level={level}
                                        count={levelSources.length}
                                        stateName={stateName}
                                        zipcode={zipcode}
                                    />
                                    <SourceGrid
                                        sources={levelSources}
                                        onSubscribe={onSubscribe}
                                        onSelect={onSelect}
                                    />
                                </div>
                            ))}
                        </div>
                    </section>
                )
            })}
        </div>
    )
}

function GovernmentLevelHeader({
    level,
    count,
    stateName,
    zipcode,
}: {
    level: GovernmentLevel
    count: number
    stateName: string | null
    zipcode: string | null
}) {
    const label =
        level === "state"
            ? (stateName ?? GOVERNMENT_LEVEL_LABELS.state)
            : level === "local" && zipcode
              ? `${GOVERNMENT_LEVEL_LABELS.local} · ${zipcode}`
              : GOVERNMENT_LEVEL_LABELS[level]

    return (
        <div className="flex items-center gap-2 border-l-2 border-border/60 pl-2">
            {level === "federal" ? (
                <span aria-hidden="true" className="text-sm leading-none">
                    🇺🇸
                </span>
            ) : level === "state" ? (
                <MapIcon className="h-3.5 w-3.5 text-muted-foreground" />
            ) : level === "local" ? (
                <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
                <Globe className="h-3.5 w-3.5 text-muted-foreground" />
            )}
            <h5 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {label}
            </h5>
            <span className="text-xs tabular-nums text-muted-foreground/70">
                {count}
            </span>
        </div>
    )
}

function SubscribedChip({ className }: { className?: string }) {
    return (
        <span
            title="Already in your library"
            className={cn(
                "inline-flex h-7 shrink-0 items-center gap-1 rounded-full border border-secondary/30 bg-secondary/10 px-2 text-xs font-medium text-secondary",
                className
            )}
        >
            <Check className="h-3 w-3" />
            Subscribed
        </span>
    )
}

function SourceCard({
    source,
    onSubscribe,
    onSelect,
}: {
    source: CatalogSource
    onSubscribe: (source: CatalogSource, feed: CatalogFeed) => void
    onSelect: (source: CatalogSource) => void
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
            <CardContent className="flex flex-1 flex-col gap-4 p-5">
                <div className="flex items-start gap-4">
                    <FeedIcon
                        feed={{
                            title: source.name,
                            image_url: faviconUrl(source.canonical_domain),
                        }}
                        className="mt-0.5 h-8 w-8 shrink-0 rounded"
                    />
                    <div className="min-w-0 flex-1">
                        <p
                            className="line-clamp-2 text-sm font-semibold leading-snug text-foreground"
                            title={source.name}
                        >
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

                <div className="mt-auto space-y-2.5">
                    {source.feeds.map((feed) => (
                        <div
                            key={feed.id}
                            className="flex items-center justify-between gap-3 rounded-md border border-border/60 bg-background/40 px-4 py-3"
                        >
                            <div className="min-w-0 space-y-0.5">
                                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                                    {feedTypeLabel(feed.feed_type)}
                                </p>
                                <p
                                    className="truncate text-xs text-muted-foreground"
                                    title={feed.feed_url}
                                >
                                    {feed.feed_url}
                                </p>
                            </div>
                            {feed.is_subscribed ? (
                                <SubscribedChip />
                            ) : (
                                <Button
                                    size="icon"
                                    variant="secondary"
                                    aria-label={`Subscribe to ${source.name}`}
                                    onClick={(event) => {
                                        event.stopPropagation()
                                        onSubscribe(source, feed)
                                    }}
                                    className="h-7 w-7 shrink-0 rounded-full"
                                >
                                    <Plus className="h-4 w-4" />
                                </Button>
                            )}
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
                                    image_url: faviconUrl(
                                        source.canonical_domain
                                    ),
                                }}
                                className="h-8 w-8 shrink-0 rounded"
                            />
                            <span className="truncate">{source.name}</span>
                        </DialogTitle>
                        <DialogDescription>
                            {source.canonical_domain} · {source.feeds.length}{" "}
                            {source.feeds.length === 1
                                ? "verified feed"
                                : "verified feeds"}
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
            <div className="flex items-center justify-between gap-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {feedTypeLabel(feed.feed_type)}
                </p>
                {feed.is_subscribed && <SubscribedChip />}
            </div>

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
                                const published = formatPublished(
                                    item.published_at
                                )
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
                                            <p className="text-xs text-muted-foreground">
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
        <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
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
                                <Skeleton
                                    key={cardIndex}
                                    className="h-32 w-full"
                                />
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
