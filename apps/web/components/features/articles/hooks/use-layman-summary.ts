"use client"

import {
    type Article,
    type LaymanSummary,
    type LaymanSummaryInput,
    useCacheLaymanSummaryMutation,
    useGenerateLaymanSummaryMutation,
    useLaymanSummaryQuery,
} from "@infrss/shared"
import { useEffect, useState } from "react"

import { prepareDocument } from "@/lib/primary/doc-cleaner"
import { generateWithOllama } from "@/lib/primary/ollama"
import { getCachedSummary, setCachedSummary } from "@/lib/primary/summary-cache"
import { generateWithWebLlm, isWebGpuAvailable } from "@/lib/primary/webllm"

export type LaymanStatus = "idle" | "generating" | "ready" | "error"
export type LaymanBackend = "server" | "webgpu" | "ollama" | "cache" | null

export interface UseLaymanSummaryResult {
    summary: LaymanSummary | null
    status: LaymanStatus
    /** Model download / generation progress, 0–1 (WebLLM only). */
    progress: number
    backend: LaymanBackend
    gpuAvailable: boolean
    isGenerating: boolean
    error: string | null
    generate: () => Promise<void>
}

/**
 * Orchestrates layman summarisation with a graceful fallback chain:
 * server cache → IndexedDB cache → on-device WebLLM (WebGPU) → local Ollama → server generation.
 *
 * A summary found on the server or in the local cache is shown immediately; generation only runs
 * on an explicit `generate()` call, so a ~1 GB model is never downloaded speculatively.
 */
export function useLaymanSummary(article: Article): UseLaymanSummaryResult {
    const query = useLaymanSummaryQuery(article.id, {
        articleType: article.article_type,
    })
    const cacheMutation = useCacheLaymanSummaryMutation()
    const generateMutation = useGenerateLaymanSummaryMutation()

    const [local, setLocal] = useState<LaymanSummary | null>(null)
    const [status, setStatus] = useState<LaymanStatus>("idle")
    const [progress, setProgress] = useState(0)
    const [backend, setBackend] = useState<LaymanBackend>(null)
    const [error, setError] = useState<string | null>(null)
    const [gpuAvailable, setGpuAvailable] = useState(false)

    useEffect(() => setGpuAvailable(isWebGpuAvailable()), [])

    const summary = query.data ?? local ?? null

    // Surface a locally-cached summary without waiting for a generate() click.
    useEffect(() => {
        let cancelled = false
        if (query.data || local) return
        getCachedSummary(article.id).then((cached) => {
            if (!cancelled && cached) {
                setLocal(cached)
                setBackend("cache")
                setStatus("ready")
            }
        })
        return () => {
            cancelled = true
        }
    }, [article.id, query.data, local])

    async function generate(): Promise<void> {
        setStatus("generating")
        setProgress(0)
        setError(null)

        const document = prepareDocument(
            article.extracted_content ??
                article.content ??
                article.description ??
                ""
        )
        const title = article.title ?? ""

        // 1. On-device WebGPU (preferred when available).
        if (gpuAvailable) {
            const result = await generateWithWebLlm(
                title,
                document,
                (_p, _t) => {
                    // Progress reports also carry text; only the numeric fraction drives the bar.
                    setProgress(_p)
                }
            )
            if (result) {
                await commit(result, "webgpu")
                return
            }
        }

        // 2. Local Ollama (only when configured).
        const ollamaResult = await generateWithOllama(title, document)
        if (ollamaResult) {
            await commit(ollamaResult, "ollama")
            return
        }

        // 3. Server fallback.
        try {
            const result = await generateMutation.mutateAsync({
                articleId: article.id,
                articleType: article.article_type,
            })
            setLocal(result)
            setBackend("server")
            setStatus("ready")
        } catch {
            setStatus("error")
            setError("Could not generate a plain-language summary.")
        }
    }

    async function commit(
        result: LaymanSummaryInput,
        source: LaymanBackend
    ): Promise<void> {
        const stored: LaymanSummary = {
            ...result,
            generated_at: new Date().toISOString(),
        }
        setLocal(stored)
        setBackend(source)
        setStatus("ready")
        await setCachedSummary(article.id, stored)
        // Share the on-device result so other users (and this user's other devices) reuse it.
        try {
            await cacheMutation.mutateAsync({
                articleId: article.id,
                input: {
                    headline: stored.headline,
                    what_happened: stored.what_happened,
                    key_impact: stored.key_impact,
                    model_identifier: stored.model_identifier,
                },
                articleType: article.article_type,
            })
        } catch {
            // Persisting for sharing is best-effort; the summary is already shown locally.
        }
    }

    return {
        summary,
        status,
        progress,
        backend,
        gpuAvailable,
        isGenerating: status === "generating",
        error,
        generate,
    }
}
