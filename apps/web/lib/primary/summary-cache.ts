import type { LaymanSummary } from "@infrss/shared"

/**
 * IndexedDB cache for generated layman summaries, keyed by article id, so a summary survives
 * reloads without another model run. Best-effort: every failure resolves to a miss/no-op.
 */

const DB_NAME = "infrss-layman"
const STORE = "summaries"
const VERSION = 1

function openDb(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        if (typeof indexedDB === "undefined") {
            reject(new Error("IndexedDB unavailable"))
            return
        }
        const request = indexedDB.open(DB_NAME, VERSION)
        request.onupgradeneeded = () => {
            if (!request.result.objectStoreNames.contains(STORE)) {
                request.result.createObjectStore(STORE)
            }
        }
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
    })
}

export async function getCachedSummary(
    key: string
): Promise<LaymanSummary | null> {
    try {
        const db = await openDb()
        return await new Promise<LaymanSummary | null>((resolve, reject) => {
            const request = db
                .transaction(STORE, "readonly")
                .objectStore(STORE)
                .get(key)
            request.onsuccess = () =>
                resolve((request.result as LaymanSummary | undefined) ?? null)
            request.onerror = () => reject(request.error)
        })
    } catch {
        return null
    }
}

export async function setCachedSummary(
    key: string,
    summary: LaymanSummary
): Promise<void> {
    try {
        const db = await openDb()
        await new Promise<void>((resolve, reject) => {
            const request = db
                .transaction(STORE, "readwrite")
                .objectStore(STORE)
                .put(summary, key)
            request.onsuccess = () => resolve()
            request.onerror = () => reject(request.error)
        })
    } catch {
        // Best-effort cache; ignore failures.
    }
}
