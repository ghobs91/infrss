"use client"

import type { Article } from "@infrss/shared"
import { ChevronDown, ChevronUp, Sparkles, X } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { prepareDocument } from "@/lib/primary/doc-cleaner"
import { cn } from "@/lib/utils"

import { PrimarySourceBadge } from "./PrimarySourceBadge"
import { WebLlmStatusIndicator } from "./WebLlmStatusIndicator"
import { useLaymanSummary } from "./hooks/use-layman-summary"

interface LaymanSummaryCardProps {
    article: Article
    className?: string
}

/**
 * Plain-language summary shown above the article body. Generation runs on-device (WebLLM) when
 * WebGPU is available, then falls back to a local Ollama endpoint, then to the server. A toggle
 * reveals the cleaned original document text.
 */
export function LaymanSummaryCard({
    article,
    className,
}: LaymanSummaryCardProps) {
    const {
        summary,
        status,
        progress,
        backend,
        gpuAvailable,
        isGenerating,
        error,
        generate,
    } = useLaymanSummary(article)
    const [showOriginal, setShowOriginal] = useState(false)
    const [dismissed, setDismissed] = useState(false)

    if (dismissed) return null

    const rawText = prepareDocument(
        article.extracted_content ??
            article.content ??
            article.description ??
            ""
    )

    if (!summary) {
        return (
            <Card className={cn("border bg-card/50 shadow-sm", className)}>
                <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-primary" />
                        <span className="text-sm text-muted-foreground">
                            {error ??
                                "Understand this document in plain language"}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        {isGenerating && (
                            <WebLlmStatusIndicator
                                gpuAvailable={gpuAvailable}
                                backend={backend}
                                status={status}
                                progress={progress}
                            />
                        )}
                        <Button
                            size="sm"
                            variant="secondary"
                            onClick={generate}
                            disabled={isGenerating}
                        >
                            {isGenerating ? "Generating…" : "Explain simply"}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className={cn("border bg-card/50 shadow-sm", className)}>
            <CardContent className="flex flex-col gap-3 p-5">
                <header className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                        <Sparkles className="h-4 w-4 shrink-0 text-primary" />
                        <h3 className="text-sm font-medium text-foreground">
                            Plain language
                        </h3>
                        {article.feed_is_primary && <PrimarySourceBadge />}
                        <WebLlmStatusIndicator
                            gpuAvailable={gpuAvailable}
                            backend={backend}
                            status={status}
                            progress={progress}
                        />
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 gap-1 px-2 text-xs"
                            onClick={() => setShowOriginal((value) => !value)}
                        >
                            {showOriginal ? (
                                <ChevronUp className="h-3 w-3" />
                            ) : (
                                <ChevronDown className="h-3 w-3" />
                            )}
                            {showOriginal ? "Hide original" : "Show original"}
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                            onClick={() => setDismissed(true)}
                            aria-label="Dismiss plain-language summary"
                        >
                            <X className="h-3.5 w-3.5" />
                        </Button>
                    </div>
                </header>

                <p className="text-sm font-medium text-foreground">
                    {summary.headline}
                </p>

                <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                    {summary.what_happened.map((bullet, index) => (
                        <li key={index}>{bullet}</li>
                    ))}
                </ul>

                <p className="text-sm text-foreground">
                    <span className="font-medium">Impact: </span>
                    {summary.key_impact}
                </p>

                {showOriginal && (
                    <div className="max-h-64 overflow-auto rounded-md border bg-muted/30 p-3 text-xs whitespace-pre-wrap text-muted-foreground">
                        {rawText || "No original text available."}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
