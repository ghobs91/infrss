"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
    SidebarGroup,
    SidebarMenu,
    SidebarMenuItem,
    useSidebarLeft,
} from "@/components/ui/sidebar"
import { useUnreadCounts } from "@infrss/shared"
import { cn } from "@/lib/utils"
import { sumFeedUnreadCounts } from "@/lib/unread-counts"

interface MainNavItem {
    /** Display title for the navigation item */
    title: string
    /** Icon component for the navigation item */
    icon: React.ElementType
    /** URL path for navigation */
    url: string
}

interface MainNavigationItemsProps {
    /** Array of main navigation items */
    items: MainNavItem[]
}

/**
 * Main navigation items component for displaying top-level navigation links.
 * Includes special count handling for the Read Later item.
 */
export function MainNavigationItems({ items }: MainNavigationItemsProps) {
    const pathname = usePathname()
    const { isMobile, toggleSidebar } = useSidebarLeft()

    // Fetch unread counts for special items
    const { data: unreadCounts } = useUnreadCounts({
        refetchOnMount: false,
        refetchOnWindowFocus: false,
        staleTime: 0, // Always consider stale so invalidation works immediately
    })

    const typedUnreadCounts =
        (unreadCounts as {
            read_later?: number
            feed_counts?: Record<string, number>
        }) || {}

    /**
     * Get unread count for specific navigation items. "All Articles" shows the same summed
     * total as the articles header so the two never disagree.
     */
    const getCountForItem = (title: string): number | null => {
        switch (title) {
            case "All Articles":
                return sumFeedUnreadCounts(typedUnreadCounts.feed_counts)
            case "Read Later":
                return typedUnreadCounts.read_later || 0
            default:
                return null
        }
    }

    return (
        <SidebarGroup>
            <SidebarMenu>
                {items.map((item) => {
                    const count = getCountForItem(item.title)
                    const isActive = pathname === item.url

                    return (
                        <SidebarMenuItem key={item.title}>
                            <div
                                className={cn(
                                    "relative flex items-center w-full group/item h-8 max-md:h-10 rounded-md text-sm transition-colors duration-150 px-1 pl-2",
                                    "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                                    isActive &&
                                        "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                                )}
                            >
                                <Link
                                    href={item.url}
                                    aria-label={`Navigate to ${item.title}`}
                                    onClick={() => {
                                        if (isMobile) toggleSidebar()
                                    }}
                                    className="flex flex-grow items-center overflow-hidden h-full pr-10 outline-none select-none text-sidebar-foreground pl-1"
                                >
                                    <item.icon className="h-4 w-4 shrink-0" />
                                    <span className="ml-2 truncate">
                                        {item.title}
                                    </span>
                                </Link>

                                {/* Count badge for applicable items positioned absolutely on the right */}
                                {count != null && count > 0 && (
                                    <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none select-none flex items-center pr-1">
                                        <span className="text-xs font-semibold text-muted-foreground/80 px-1.5 py-0.5 rounded-full bg-muted/40 backdrop-blur-xs">
                                            {count}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </SidebarMenuItem>
                    )
                })}
            </SidebarMenu>
        </SidebarGroup>
    )
}

export type { MainNavItem }
