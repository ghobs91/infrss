import {
    CreateWebWorkerMLCEngine,
    type InitProgressReport,
    type MLCEngineInterface,
} from "@mlc-ai/web-llm"
import type { LaymanSummaryInput } from "@infrss/shared"

import {
    buildLaymanPrompt,
    LAYMAN_SYSTEM_PROMPT,
    parseLaymanSummary,
} from "./prompt"

/**
 * On-device WebLLM engine (WebGPU). The model is loaded lazily on first use and the engine is a
 * module singleton, so repeated generations reuse the loaded weights.
 */

export const DEFAULT_WEBLLM_MODEL = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC"
export const LOW_MEMORY_WEBLLM_MODEL = "Llama-3.2-1B-Instruct-q4f16_1-MLC"

export type WebLlmProgress = (progress: number, text: string) => void

let enginePromise: Promise<MLCEngineInterface> | null = null

export function isWebGpuAvailable(): boolean {
    return typeof navigator !== "undefined" && "gpu" in navigator
}

function selectedModel(): string {
    return process.env.NEXT_PUBLIC_WEBLLM_MODEL || DEFAULT_WEBLLM_MODEL
}

function getEngine(onProgress?: WebLlmProgress): Promise<MLCEngineInterface> {
    if (enginePromise) return enginePromise
    const worker = new Worker(
        new URL("../../workers/summarizer.worker.ts", import.meta.url),
        {
            type: "module",
        }
    )
    const created = CreateWebWorkerMLCEngine(worker, selectedModel(), {
        initProgressCallback: (report: InitProgressReport) =>
            onProgress?.(report.progress, report.text),
    })
    enginePromise = created
    return created
}

/** Release the engine and free GPU memory. */
export function resetWebLlmEngine(): void {
    enginePromise?.then((engine) => engine.unload()).catch(() => undefined)
    enginePromise = null
}

export async function generateWithWebLlm(
    title: string,
    document: string,
    onProgress?: WebLlmProgress
): Promise<LaymanSummaryInput | null> {
    try {
        const engine = await getEngine(onProgress)
        const reply = await engine.chat.completions.create({
            messages: [
                { role: "system", content: LAYMAN_SYSTEM_PROMPT },
                { role: "user", content: buildLaymanPrompt(title, document) },
            ],
            temperature: 0.2,
            max_tokens: 800,
        })
        const parsed = parseLaymanSummary(reply.choices?.[0]?.message?.content)
        return parsed ? { ...parsed, model_identifier: selectedModel() } : null
    } catch {
        // Any WebGPU/model failure falls through to the next backend in the orchestrator.
        return null
    }
}
