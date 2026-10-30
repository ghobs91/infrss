"use client"

import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuSub,
    DropdownMenuSubContent,
    DropdownMenuSubTrigger,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"
import { useIsMobile } from "@/hooks/use-mobile"
import { colorTokens } from "@infrss/design-tokens"
import {
    ArrowLeft,
    BookmarkIcon,
    Check,
    Copy,
    ExternalLink,
    FileText,
    Globe,
    Languages,
    Loader2,
    MoreHorizontal,
    Sparkles,
    TextSelection,
} from "lucide-react"
import { useState } from "react"
import { toast } from "react-hot-toast"
import { LanguageSelector } from "./LanguageSelector"
import { ContentView, type Article } from "@infrss/shared"

interface ArticleToolbarProps {
    hideBackground?: boolean
    article: Article
    contentView: ContentView
    setContentView: (view: ContentView) => void
    handleMarkAsRead: () => void
    handleToggleReadLater: () => void
    handleExtractContent: () => void
    handleSummarize: () => void
    handleTranslate: (language: string) => void
    handleToggleHighlights: () => void
    isExtracting: boolean
    isSummarizing: boolean
    isTranslating: boolean
    isHighlighting: boolean
    highlightsEnabled: boolean
    onBack?: () => void
    isReadLaterMode: boolean
    translatedContent: string | null
    translatedLanguage: string | null
    isSaved?: boolean
    isRead?: boolean
    isPreviewMode?: boolean
}

export function ArticleToolbar({
    hideBackground = false,
    article,
    contentView,
    setContentView,
    handleMarkAsRead,
    handleToggleReadLater,
    handleExtractContent,
    handleSummarize,
    handleTranslate,
    handleToggleHighlights,
    isExtracting,
    isSummarizing,
    isTranslating,
    isHighlighting,
    highlightsEnabled,
    onBack,
    isReadLaterMode,
    translatedContent,
    translatedLanguage,
    isSaved,
    isPreviewMode = false,
}: ArticleToolbarProps) {
    const [showLanguageSelector, setShowLanguageSelector] = useState(false)
    const isMobile = useIsMobile()

    const hasTranslatedContent = !!translatedContent
    const effectiveIsSaved = isSaved ?? article.is_saved

    const handleCopyUrl = async () => {
        if (!article.link) {
            toast.error("No URL available to copy")
            return
        }

        try {
            await navigator.clipboard.writeText(article.link)
            toast.success("URL copied to clipboard")
        } catch {
            toast.error(
                "Failed to copy URL. HTTPS required for clipboard access"
            )
        }
    }

    const handleOpenOriginal = () => {
        if (article.link) {
            window.open(article.link, "_blank", "noopener,noreferrer")
        } else {
            toast.error("No original URL available")
        }
    }

    const handleTranslateClick = (language: string) => {
        setShowLanguageSelector(false)
        handleTranslate(language)
    }

    return (
        <div
            className={`flex items-center gap-1 ${isMobile && onBack ? "justify-between" : "justify-end"} ${hideBackground ? "gap-1" : "px-4 py-3 bg-background/95 backdrop-blur-sm border-b"}`}
        >
            {/* Mobile back button - shown when onBack is provided */}
            {isMobile && onBack && (
                <div className="flex items-center">
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="glass-control h-9 w-9 rounded-full p-0"
                                    onClick={onBack}
                                    title="Back to articles"
                                >
                                    <ArrowLeft className="h-4 w-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>Back to articles</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>
            )}
            <div
                className={`flex items-center ${isMobile ? "gap-1 flex-1 min-w-0 justify-end" : "gap-1"}`}
            >
                {/* Content Source Tabs - Show when link is available and not a newsletter */}
                {article.link &&
                    !article.link.startsWith("newsletter://") &&
                    setContentView &&
                    (article.article_type !== "clipped" ||
                        hasTranslatedContent) && (
                        <div
                            className={`${isMobile ? "mr-0 flex-1 min-w-0" : "mr-2"}`}
                        >
                            <Tabs
                                value={contentView}
                                onValueChange={(value) => {
                                    const newView = value as ContentView

                                    // If switching to extracted and no content exists yet, trigger extraction
                                    // which switches the view to Extracted immediately
                                    if (
                                        newView === ContentView.Extracted &&
                                        !article.extracted_content
                                    ) {
                                        handleExtractContent()
                                        return
                                    }

                                    // Otherwise switch immediately
                                    setContentView(newView)
                                }}
                                className={`${isMobile ? "w-full" : "w-auto inline-block"}`}
                            >
                                <TabsList className="h-8 max-md:h-9 max-md:w-full max-md:rounded-full max-md:border max-md:border-white/50 max-md:bg-white/35 max-md:backdrop-blur-xl dark:max-md:border-white/10 dark:max-md:bg-white/10">
                                    <TabsTrigger
                                        value={ContentView.Original}
                                        title="Original RSS content"
                                        className="h-7 px-2 max-md:h-7 max-md:flex-1"
                                    >
                                        <FileText className="h-4 w-4" />
                                    </TabsTrigger>
                                    {article.article_type !== "clipped" && (
                                        <TabsTrigger
                                            value={ContentView.Extracted}
                                            title="Full article content"
                                            className="h-7 px-2 max-md:h-7 max-md:flex-1"
                                        >
                                            {isExtracting ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Globe className="h-4 w-4" />
                                            )}
                                        </TabsTrigger>
                                    )}
                                    {hasTranslatedContent && (
                                        <TabsTrigger
                                            value={ContentView.Translated}
                                            title={`Translated content${translatedLanguage ? ` (${translatedLanguage})` : ""}`}
                                            className="h-7 px-2 max-md:h-7 max-md:flex-1"
                                        >
                                            <Languages className="h-4 w-4" />
                                        </TabsTrigger>
                                    )}
                                </TabsList>
                            </Tabs>
                        </div>
                    )}
                <TooltipProvider>
                    {!isPreviewMode && (
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <button
                                    type="button"
                                    className={`${isMobile ? "h-9 w-9 glass-control rounded-full" : "h-8 w-8"} flex items-center justify-center p-0 transition-transform duration-200 hover:scale-110 focus:outline-none`}
                                    onClick={
                                        isReadLaterMode
                                            ? handleMarkAsRead
                                            : handleToggleReadLater
                                    }
                                >
                                    {isReadLaterMode ? (
                                        <Check
                                            className="h-4 w-4"
                                            style={{
                                                color: effectiveIsSaved
                                                    ? colorTokens.primary
                                                          .DEFAULT
                                                    : colorTokens.muted
                                                          .foreground,
                                            }}
                                        />
                                    ) : (
                                        <BookmarkIcon
                                            className={`h-4 w-4 ${effectiveIsSaved ? "scale-110" : ""}`}
                                            style={{
                                                fill: effectiveIsSaved
                                                    ? "#eab308"
                                                    : "transparent",
                                                color: effectiveIsSaved
                                                    ? "#eab308"
                                                    : colorTokens.foreground,
                                            }}
                                        />
                                    )}
                                </button>
                            </TooltipTrigger>
                            <TooltipContent>
                                {isReadLaterMode
                                    ? "Mark as Read & Remove"
                                    : effectiveIsSaved
                                      ? "Remove from Read Later"
                                      : "Save for Later"}
                            </TooltipContent>
                        </Tooltip>
                    )}

                    {/* Open Original */}
                    {!isMobile &&
                        !article.link?.startsWith("newsletter://") && (
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={`${isMobile ? "h-9 w-9" : "h-8 w-8"} p-0 transition-all duration-200 hover:scale-110 hover:bg-muted/60`}
                                        onClick={handleOpenOriginal}
                                        disabled={!article.link}
                                    >
                                        <ExternalLink className="h-4 w-4" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                    {article.link
                                        ? "Open Original Article"
                                        : "No original URL available"}
                                </TooltipContent>
                            </Tooltip>
                        )}

                    {/* Copy URL */}
                    {!isMobile &&
                        !article.link?.startsWith("newsletter://") && (
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={`${isMobile ? "h-9 w-9" : "h-8 w-8"} p-0 transition-all duration-200 hover:scale-110 hover:bg-muted/60`}
                                        onClick={handleCopyUrl}
                                        disabled={!article.link}
                                    >
                                        <Copy className="h-4 w-4" />
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                    {article.link
                                        ? "Copy URL"
                                        : "No URL to copy"}
                                </TooltipContent>
                            </Tooltip>
                        )}

                    {!isMobile && !isPreviewMode && (
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className={`${isMobile ? "h-9 w-9" : "h-8 w-8"} p-0 transition-all duration-200 hover:scale-110 hover:bg-muted/60`}
                                    onClick={handleSummarize}
                                    disabled={isSummarizing}
                                >
                                    {isSummarizing ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Sparkles className="h-4 w-4" />
                                    )}
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                                {isSummarizing ? "Generating..." : "The Gist"}
                            </TooltipContent>
                        </Tooltip>
                    )}

                    {!isMobile &&
                        !isPreviewMode &&
                        !article.link?.startsWith("newsletter://") && (
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={`${isMobile ? "h-9 w-9" : "h-8 w-8"} p-0 transition-all duration-200 hover:scale-110 hover:bg-muted/60 ${highlightsEnabled ? "bg-muted/60" : ""}`}
                                        onClick={handleToggleHighlights}
                                        disabled={isHighlighting}
                                    >
                                        {isHighlighting ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <TextSelection
                                                className="h-4 w-4"
                                                style={{
                                                    color: highlightsEnabled
                                                        ? colorTokens.primary
                                                              .DEFAULT
                                                        : undefined,
                                                }}
                                            />
                                        )}
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                    {isHighlighting
                                        ? "Generating..."
                                        : highlightsEnabled
                                          ? "Hide AI Highlights"
                                          : "AI Highlights"}
                                </TooltipContent>
                            </Tooltip>
                        )}

                    {!isMobile &&
                        !isPreviewMode &&
                        !article.link?.startsWith("newsletter://") && (
                            <DropdownMenu
                                open={showLanguageSelector}
                                onOpenChange={setShowLanguageSelector}
                            >
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <DropdownMenuTrigger asChild>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className={`${isMobile ? "h-9 w-9" : "h-8 w-8"} p-0 transition-all duration-200 hover:scale-110 hover:bg-muted/60`}
                                                disabled={isTranslating}
                                            >
                                                {isTranslating ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <Languages className="h-4 w-4" />
                                                )}
                                            </Button>
                                        </DropdownMenuTrigger>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {isTranslating
                                            ? "Translating..."
                                            : "Translate Article"}
                                    </TooltipContent>
                                </Tooltip>
                                <DropdownMenuContent
                                    align="end"
                                    className="w-56"
                                >
                                    <LanguageSelector
                                        onSelect={handleTranslateClick}
                                    />
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                </TooltipProvider>

                {/* Mobile: keep the bar to back / source tabs / save / more */}
                {isMobile && (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                aria-label="More article actions"
                                className="glass-control h-9 w-9 rounded-full p-0"
                            >
                                <MoreHorizontal className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                            align="end"
                            sideOffset={8}
                            className="w-56 rounded-2xl border-border/60 bg-popover/95 p-1.5 shadow-xl backdrop-blur-xl"
                        >
                            {!article.link?.startsWith("newsletter://") && (
                                <DropdownMenuItem
                                    disabled={!article.link}
                                    onClick={handleOpenOriginal}
                                    className="gap-2 py-2.5"
                                >
                                    <ExternalLink className="h-4 w-4" />
                                    Open original
                                </DropdownMenuItem>
                            )}
                            {!article.link?.startsWith("newsletter://") && (
                                <DropdownMenuItem
                                    disabled={!article.link}
                                    onClick={handleCopyUrl}
                                    className="gap-2 py-2.5"
                                >
                                    <Copy className="h-4 w-4" />
                                    Copy link
                                </DropdownMenuItem>
                            )}
                            {!isPreviewMode && (
                                <>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem
                                        disabled={isSummarizing}
                                        onClick={handleSummarize}
                                        className="gap-2 py-2.5"
                                    >
                                        {isSummarizing ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Sparkles className="h-4 w-4" />
                                        )}
                                        The Gist
                                    </DropdownMenuItem>
                                </>
                            )}
                            {!isPreviewMode &&
                                !article.link?.startsWith("newsletter://") && (
                                    <DropdownMenuItem
                                        disabled={isHighlighting}
                                        onClick={handleToggleHighlights}
                                        className="gap-2 py-2.5"
                                    >
                                        {isHighlighting ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <TextSelection className="h-4 w-4" />
                                        )}
                                        {highlightsEnabled
                                            ? "Hide AI highlights"
                                            : "AI highlights"}
                                    </DropdownMenuItem>
                                )}
                            {!isPreviewMode &&
                                !article.link?.startsWith("newsletter://") && (
                                    <DropdownMenuSub>
                                        <DropdownMenuSubTrigger
                                            disabled={isTranslating}
                                            className="gap-2 py-2.5"
                                        >
                                            {isTranslating ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <Languages className="h-4 w-4" />
                                            )}
                                            Translate
                                        </DropdownMenuSubTrigger>
                                        <DropdownMenuSubContent className="max-h-[60vh] w-56 overflow-y-auto rounded-2xl">
                                            <LanguageSelector
                                                onSelect={handleTranslateClick}
                                                selectedLanguage={
                                                    translatedLanguage ??
                                                    undefined
                                                }
                                            />
                                        </DropdownMenuSubContent>
                                    </DropdownMenuSub>
                                )}
                        </DropdownMenuContent>
                    </DropdownMenu>
                )}
            </div>
        </div>
    )
}
