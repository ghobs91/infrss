import { SidebarLeftTrigger } from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

interface DiscoverLayoutProps {
    children: React.ReactNode
    centerVertically?: boolean
}

/**
 * Layout wrapper for the discover page
 */
export function DiscoverLayout({
    children,
    centerVertically = false,
}: DiscoverLayoutProps) {
    return (
        <div
            className={cn(
                "flex flex-col flex-1 h-svh md:h-[calc(100svh-1rem)]",
                centerVertically ? "overflow-hidden" : "overflow-y-auto"
            )}
        >
            <div className="flex shrink-0 items-center px-2 pt-[calc(0.5rem+env(safe-area-inset-top,0px))] md:px-3 md:pt-2">
                <SidebarLeftTrigger />
            </div>
            <main
                className={cn(
                    "flex-1 px-4 pb-[var(--mobile-dock-clearance)] pt-1 md:px-6 md:pb-6 md:pt-1",
                    centerVertically &&
                        "flex items-center justify-center overflow-hidden"
                )}
            >
                {children}
            </main>
        </div>
    )
}
