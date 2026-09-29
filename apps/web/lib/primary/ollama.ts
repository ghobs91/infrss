import type { LaymanSummaryInput } from "@infrss/shared"

import {
    buildLaymanPrompt,
    LAYMAN_SYSTEM_PROMPT,
    parseLaymanSummary,
} from "./prompt"

/**
 * Optional fallback: a local Ollama instance's OpenAI-compatible endpoint. Enabled only when
 * `NEXT_PUBLIC_OLLAMA_URL` is set (e.g. http://localhost:11434).
 */

const DEFAULT_MODEL = "llama3.2"

export function getOllamaEndpoint(): string | null {
    const url = process.env.NEXT_PUBLIC_OLLAMA_URL
    return url && url.trim() ? url.replace(/\/$/, "") : null
}

export async function generateWithOllama(
    title: string,
    document: string,
    options?: { endpoint?: string; model?: string }
): Promise<LaymanSummaryInput | null> {
    const endpoint = options?.endpoint ?? getOllamaEndpoint()
    if (!endpoint) return null
    const model =
        options?.model ?? process.env.NEXT_PUBLIC_OLLAMA_MODEL ?? DEFAULT_MODEL

    try {
        const response = await fetch(`${endpoint}/v1/chat/completions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                model,
                temperature: 0.2,
                max_tokens: 800,
                messages: [
                    { role: "system", content: LAYMAN_SYSTEM_PROMPT },
                    {
                        role: "user",
                        content: buildLaymanPrompt(title, document),
                    },
                ],
            }),
        })
        if (!response.ok) return null
        const data = (await response.json()) as {
            choices?: { message?: { content?: string } }[]
        }
        const parsed = parseLaymanSummary(data.choices?.[0]?.message?.content)
        return parsed
            ? { ...parsed, model_identifier: `ollama:${model}` }
            : null
    } catch {
        return null
    }
}
