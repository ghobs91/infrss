import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { SidebarLeftTrigger } from "@/components/ui/sidebar"
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"
import { CheckCheck, Eye, EyeOff, RefreshCw } from "lucide-react"
interface ArticlesHeaderProps {
    sidebarTitle: string
    unreadCount: number
    showUnreadOnly: boolean
    isReadLaterMode: boolean
    isRecentlyReadMode: boolean
    feedId?: string
    folderId?: string
    isRefreshing: boolean
    isMarkingAllRead: boolean
    toggleShowUnreadOnly: () => void
    handleRefresh: () => void
    handleMarkAllAsRead: () => void
    isPreviewMode?: boolean
}

export function ArticlesHeader({
    sidebarTitle,
    unreadCount,
    showUnreadOnly,
    isReadLaterMode,
    isRecentlyReadMode,
    feedId,
    folderId,
    isRefreshing,
    isMarkingAllRead,
    toggleShowUnreadOnly,
    handleRefresh,
    handleMarkAllAsRead,
    isPreviewMode = false,
}: ArticlesHeaderProps) {
    return (
        <div className="flex-shrink-0 flex items-center justify-between border-b px-3 py-3 gap-2 min-h-[60px] pt-[calc(0.75rem+env(safe-area-inset-top,0px))] md:px-4">
            <div className="flex items-center gap-2 flex-1 min-w-0">
                <SidebarLeftTrigger className="flex-shrink-0" />
                <h1 className="text-lg font-semibold truncate">
                    {sidebarTitle}
                </h1>
                {unreadCount > 0 && (
                    <Badge
                        variant="outline"
                        className="min-w-3 px-2 flex-shrink-0"
                    >
                        {unreadCount}
                    </Badge>
                )}
            </div>
            {!isPreviewMode && (
                <div className="flex items-center gap-1.5 flex-shrink-0">
                    {!isReadLaterMode && !isRecentlyReadMode && (
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        aria-pressed={showUnreadOnly}
                                        className={`h-8 w-8 max-md:h-9 max-md:w-9 max-md:glass-control max-md:rounded-full ${showUnreadOnly ? "bg-secondary/15 text-secondary hover:bg-secondary/25 hover:text-secondary" : ""}`}
                                        onClick={toggleShowUnreadOnly}
                                    >
                                        {showUnreadOnly ? (
                                            <Eye className="h-4 w-4" />
                                        ) : (
                                            <EyeOff className="h-4 w-4" />
                                        )}
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                    {showUnreadOnly
                                        ? "Show all articles"
                                        : "Show unread only"}
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    )}
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="hidden h-8 w-8 md:inline-flex"
                                    onClick={handleRefresh}
                                    disabled={isRefreshing}
                                >
                                    <RefreshCw
                                        className={`h-4 w-4 ${
                                            isRefreshing ? "animate-spin" : ""
                                        }`}
                                    />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Refresh feeds</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                    {(feedId || folderId) && (
                        <TooltipProvider>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 max-md:h-9 max-md:w-9 max-md:glass-control max-md:rounded-full"
                                        onClick={handleMarkAllAsRead}
                                        disabled={isMarkingAllRead}
                                    >
                                        <CheckCheck className="h-4 w-4" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                    Mark all as read
                                </TooltipContent>
                            </Tooltip>
                        </TooltipProvider>
                    )}
                </div>
            )}
        </div>
    )
}
