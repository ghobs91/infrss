/**
 * Client-side document cleaning for on-device summarisation.
 *
 * Mirrors `server/app/services/catalog/doc_cleaner.py`: strip boilerplate, isolate the
 * load-bearing sections, and cap the prompt. Kept as a parallel implementation because the
 * on-device path runs in the browser and cannot call Python.
 */

const SECTION_MARKERS: { kind: string; patterns: RegExp[] }[] = [
    {
        kind: "sec_10k",
        patterns: [
            /Management'?s Discussion and Analysis/i,
            /\bRisk Factors\b/i,
        ],
    },
    { kind: "sec_8k", patterns: [/Item\s+\d\.\d{2}/i] },
    {
        kind: "gov_reg",
        patterns: [
            /\bSupplementary Information\b/i,
            /\bSummary\b/i,
            /\bAction\b/i,
        ],
    },
]

const CHARS_PER_TOKEN = 4

export function stripHtml(html: string): string {
    if (!html) return ""
    if (typeof window === "undefined" || typeof DOMParser === "undefined") {
        return html
            .replace(/<[^>]+>/g, " ")
            .replace(/\s+/g, " ")
            .trim()
    }
    const doc = new DOMParser().parseFromString(html, "text/html")
    doc.querySelectorAll(
        "script, style, nav, header, footer, aside, noscript"
    ).forEach((node) => node.remove())
    return (doc.body?.textContent ?? "").replace(/\s+/g, " ").trim()
}

export function detectDocumentKind(text: string): string | null {
    for (const { kind, patterns } of SECTION_MARKERS) {
        if (patterns.some((pattern) => pattern.test(text))) return kind
    }
    return null
}

export function extractSections(
    text: string,
    patterns: RegExp[],
    maxChars: number
): string {
    const combined = new RegExp(
        patterns.map((p) => `(${p.source})`).join("|"),
        "gi"
    )
    const matches = Array.from(text.matchAll(combined))
    if (matches.length === 0) return text.slice(0, maxChars)

    const segments: string[] = []
    for (let i = 0; i < matches.length; i++) {
        const start = matches[i]?.index ?? 0
        const end = matches[i + 1]?.index ?? text.length
        segments.push(text.slice(start, end).trim())
    }
    return segments.join("\n\n").slice(0, maxChars)
}

export function truncateToTokens(
    text: string,
    maxTokens: number,
    charsPerToken: number = CHARS_PER_TOKEN
): string {
    const limit = maxTokens * charsPerToken
    if (text.length <= limit) return text
    const cut = text.slice(0, limit)
    const lastSpace = cut.lastIndexOf(" ")
    return lastSpace > 0 ? cut.slice(0, lastSpace) : cut
}

export function prepareDocument(content: string, maxTokens = 3000): string {
    let text = stripHtml(content)
    const kind = detectDocumentKind(text)
    if (kind) {
        const marker = SECTION_MARKERS.find((entry) => entry.kind === kind)
        if (marker) {
            text = extractSections(
                text,
                marker.patterns,
                maxTokens * CHARS_PER_TOKEN
            )
        }
    }
    return truncateToTokens(text, maxTokens)
}
