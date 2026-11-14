"use client"

import { useArticlesStore } from "@/components/features/articles/stores/use-articles-store"
import { useSidebarLeft } from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"
import { useUnreadCounts } from "@infrss/shared"
import { sumFeedUnreadCounts } from "@/lib/unread-counts"
import { motion } from "framer-motion"
import { BookmarkIcon, Compass, Newspaper, Rss, Sparkles } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

const DOCK_ITEMS = [
    { label: "Articles", href: "/articles", icon: Newspaper, badge: null },
    { label: "Digest", href: "/codex", icon: Sparkles, badge: null },
    { label: "Discover", href: "/discover", icon: Compass, badge: null },
    {
        label: "Saved",
        href: "/read-later",
        icon: BookmarkIcon,
        badge: "read_later",
    },
] as const

/** Routes whose detail view should take over the full screen on mobile. */
const ARTICLE_ROUTE =
    /^\/(articles|read-later|recently-read|feeds|folders)(\/|$)/

/**
 * Floating Liquid Glass navigation dock for mobile web.
 *
 * The primary destinations stay one thumb-reach away on every route (previously Discover and
 * Codex had no navigation affordance at all), while "Feeds" opens the existing sidebar sheet
 * for feeds, folders and the account menu. Hidden while an article is open so reading gets
 * the full screen, matching a native push.
 */
export function MobileDock() {
    const pathname = usePathname()
    const { toggleSidebar } = useSidebarLeft()
    const viewMode = useArticlesStore((state) => state.viewMode)
    const { data: unreadCounts } = useUnreadCounts()
    const counts = unreadCounts as
        | { read_later?: number; feed_counts?: Record<string, number> }
        | undefined

    const isReading =
        /^\/articles\/[^/]+$/.test(pathname) ||
        (ARTICLE_ROUTE.test(pathname) && viewMode === "content")

    if (isReading) return null

    return (
        <nav
            aria-label="Primary"
            className="pointer-events-none fixed inset-x-0 bottom-0 z-[900] flex justify-center md:hidden"
            style={{
                paddingBottom:
                    "calc(env(safe-area-inset-bottom, 0px) + var(--mobile-dock-offset))",
            }}
        >
            <div className="glass-surface pointer-events-auto mx-3 flex w-[calc(100%-1.5rem)] max-w-[420px] items-stretch gap-0.5 rounded-[26px] p-1.5">
                {DOCK_ITEMS.map((item) => {
                    const isArticleView =
                        item.href === "/articles" &&
                        /^\/(articles|recently-read|feeds|folders)(\/|$)/.test(
                            pathname
                        )
                    const isActive = pathname === item.href || isArticleView
                    // "Articles" is the home view, so it carries the summed unread total.
                    const count = item.badge
                        ? Number(counts?.[item.badge] ?? 0)
                        : item.href === "/articles"
                          ? sumFeedUnreadCounts(counts?.feed_counts)
                          : 0

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            aria-current={isActive ? "page" : undefined}
                            className={cn(
                                "relative flex min-h-12 flex-1 touch-manipulation flex-col items-center justify-center gap-0.5 rounded-[20px] px-1 py-1.5 outline-none transition-[color,transform] duration-150 active:scale-95 focus-visible:ring-2 focus-visible:ring-ring",
                                isActive
                                    ? "text-foreground"
                                    : "text-muted-foreground"
                            )}
                        >
                            {isActive && (
                                <motion.span
                                    layoutId="mobile-dock-active"
                                    className="absolute inset-0 rounded-[20px] bg-white/45 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.7)] dark:bg-white/12 dark:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.16)]"
                                    transition={{
                                        type: "spring",
                                        stiffness: 520,
                                        damping: 40,
                                    }}
                                />
                            )}
                            <span className="relative flex items-center justify-center">
                                <item.icon
                                    className="size-5"
                                    strokeWidth={isActive ? 2.4 : 1.9}
                                />
                                {count > 0 && (
                                    <span className="absolute -right-2.5 -top-1.5 min-w-4 rounded-full bg-primary px-1 text-center text-[0.75rem] font-bold leading-4 text-primary-foreground">
                                        {count > 99 ? "99+" : count}
                                    </span>
                                )}
                            </span>
                            <span className="relative text-xs font-medium leading-tight">
                                {item.label}
                            </span>
                        </Link>
                    )
                })}

                <span
                    aria-hidden="true"
                    className="my-2 w-px shrink-0 bg-black/10 dark:bg-white/12"
                />

                <button
                    type="button"
                    onClick={toggleSidebar}
                    aria-label="Open feeds and account menu"
                    className="flex min-h-12 flex-1 touch-manipulation flex-col items-center justify-center gap-0.5 rounded-[20px] px-1 py-1.5 text-muted-foreground outline-none transition-[color,transform] duration-150 active:scale-95 focus-visible:ring-2 focus-visible:ring-ring active:text-foreground"
                >
                    <Rss className="size-5" strokeWidth={1.9} />
                    <span className="text-xs font-medium leading-tight">
                        Feeds
                    </span>
                </button>
            </div>
        </nav>
    )
}
