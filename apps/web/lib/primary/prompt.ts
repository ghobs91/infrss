import type { LaymanSummaryInput } from "@infrss/shared"

/**
 * Plain-language translation prompt. Kept byte-identical to the server prompt in
 * `server/app/services/ai/prompts.py` (LAYMAN_SUMMARY_SYSTEM_PROMPT) so on-device, Ollama and
 * server output share one contract. Change both together.
 */
export const LAYMAN_SYSTEM_PROMPT = `You are a plain-language translator for a primary-source news system.
Translate dense legal, corporate, or governmental disclosures into accurate, jargon-free bullet
points for non-experts.

STRICT RULES:
1. Do NOT use undefined technical jargon. Explain required terms briefly in parentheses.
2. Base output strictly on provided text. Do not invent details or provide financial advice.
3. You MUST respond in valid JSON using this structure:

{
  "headline": "Single sentence summarizing the principal core action or event.",
  "whatHappened": [
    "Fact-based bullet point detailing what occurred (include figures, dates, or key parties).",
    "Fact-based bullet point detailing specific scope or direct actions taken."
  ],
  "keyImpact": "1-2 sentences on practical real-world impact or regulatory requirement."
}`

export function buildLaymanPrompt(title: string, document: string): string {
    return `Title: ${title}\n\nDocument:\n${document}`
}

const FENCE_RE = /^```(?:json)?\s*|\s*```$/gm

/** Parse a model response into the layman-summary shape, tolerating markdown-fenced JSON. */
export function parseLaymanSummary(
    raw: string | null | undefined
): Omit<LaymanSummaryInput, "model_identifier"> | null {
    if (!raw) return null
    const cleaned = raw.trim().replace(FENCE_RE, "").trim()
    try {
        const data: unknown = JSON.parse(cleaned)
        if (!data || typeof data !== "object") return null
        const { headline, whatHappened, keyImpact } = data as Record<
            string,
            unknown
        >
        if (typeof headline !== "string" || typeof keyImpact !== "string")
            return null
        if (
            !Array.isArray(whatHappened) ||
            !whatHappened.every((bullet) => typeof bullet === "string")
        ) {
            return null
        }
        const bullets = (whatHappened as string[])
            .map((b) => b.trim())
            .filter(Boolean)
        if (!headline.trim() || !keyImpact.trim() || bullets.length === 0)
            return null
        return {
            headline: headline.trim(),
            what_happened: bullets,
            key_impact: keyImpact.trim(),
        }
    } catch {
        return null
    }
}
