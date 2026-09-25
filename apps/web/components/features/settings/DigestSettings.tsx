"use client"

import {
    useCodexPreferences,
    useFeeds,
    useUpdateCodexPreferences,
} from "@infrss/shared"
import { useCallback, useMemo, useState } from "react"
import { toast } from "react-hot-toast"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { SettingsSection } from "./SettingsSection"

/**
 * Which folders feed the Daily Digest. Every folder is included by default; toggling one off
 * drops its feeds from the next generation (not the digest already on screen). State mirrors
 * the server unless the user has unsaved edits, so a late fetch can't clobber an edit.
 */
export function DigestSettings() {
    const [draft, setDraft] = useState<Set<string> | null>(null)

    const { data: feedsResponse, isLoading: feedsLoading } = useFeeds({})
    const { data: prefs, isLoading: prefsLoading } = useCodexPreferences()
    const updatePreferences = useUpdateCodexPreferences()

    const folders = useMemo(
        () =>
            [...(feedsResponse?.folders ?? [])].sort((a, b) =>
                a.name.localeCompare(b.name)
            ),
        [feedsResponse]
    )

    const serverExcluded = useMemo(
        () => new Set(prefs?.excluded_folder_ids ?? []),
        [prefs]
    )
    const excluded = draft ?? serverExcluded

    const dirty =
        draft !== null &&
        (draft.size !== serverExcluded.size ||
            [...draft].some((id) => !serverExcluded.has(id)))

    const loading = feedsLoading || prefsLoading

    const toggle = useCallback(
        (folderId: string, included: boolean) => {
            setDraft((prev) => {
                const base = prev ?? new Set(serverExcluded)
                const next = new Set(base)
                if (included) next.delete(folderId)
                else next.add(folderId)
                return next
            })
        },
        [serverExcluded]
    )

    const handleSave = useCallback(async () => {
        if (!draft) return
        try {
            await toast.promise(
                updatePreferences.mutateAsync({
                    excluded_folder_ids: [...draft],
                }),
                {
                    loading: "Saving digest settings…",
                    success: "Digest settings saved",
                    error: "Couldn't save digest settings",
                }
            )
            setDraft(null)
        } catch {
            // toast.promise surfaced it; keep the edit for a retry.
        }
    }, [draft, updatePreferences])

    return (
        <SettingsSection
            title="Daily Digest"
            description="Choose which folders feed your digest. Changes take effect the next time a digest is built."
        >
            {loading ? (
                <div className="space-y-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div
                            key={i}
                            className="flex items-center justify-between"
                        >
                            <Skeleton className="h-4 w-40" />
                            <Skeleton className="h-6 w-10 rounded-full" />
                        </div>
                    ))}
                </div>
            ) : folders.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                    You don&apos;t have any folders yet. Organise your feeds
                    into folders to control what your digest reads.
                </p>
            ) : (
                <div className="flex flex-col gap-4">
                    <ul className="divide-y divide-border/60">
                        {folders.map((folder) => {
                            const included = !excluded.has(folder.id)
                            return (
                                <li
                                    key={folder.id}
                                    className="flex items-center justify-between gap-4 py-3"
                                >
                                    <label
                                        htmlFor={`digest-folder-${folder.id}`}
                                        className="min-w-0 flex-1 cursor-pointer truncate text-sm"
                                    >
                                        {folder.name}
                                    </label>
                                    <Switch
                                        id={`digest-folder-${folder.id}`}
                                        checked={included}
                                        onCheckedChange={(checked) =>
                                            toggle(folder.id, checked)
                                        }
                                    />
                                </li>
                            )
                        })}
                    </ul>
                    <div className="flex justify-end">
                        <Button
                            onClick={handleSave}
                            disabled={
                                !dirty || loading || updatePreferences.isPending
                            }
                        >
                            {updatePreferences.isPending ? "Saving…" : "Save"}
                        </Button>
                    </div>
                </div>
            )}
        </SettingsSection>
    )
}
