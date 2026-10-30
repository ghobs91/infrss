"use client"

import {
    ApiError,
    type CatalogFeed,
    type CatalogSource,
    useCreateFolder,
    useFeeds,
    useSubscribeCatalogFeedMutation,
} from "@infrss/shared"
import { Loader2, Rss } from "lucide-react"
import { useMemo, useState } from "react"
import { toast } from "react-hot-toast"

import { FolderSelect } from "@/components/features/feeds/FolderSelect"
import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"

interface CatalogSubscribeDialogProps {
    source: CatalogSource
    feed: CatalogFeed
    onClose: () => void
}

/**
 * Folder picker shown before subscribing to a catalog feed. Mirrors the feed-URL subscription
 * dialog: a folder is required, and a new one can be created inline.
 */
export function CatalogSubscribeDialog({
    source,
    feed,
    onClose,
}: CatalogSubscribeDialogProps) {
    const { data: feedsResponse, isLoading: feedsLoading } = useFeeds({})
    const folders = useMemo(() => feedsResponse?.folders ?? [], [feedsResponse])

    const [selectedFolderId, setSelectedFolderId] = useState("")
    const [isCreatingFolder, setIsCreatingFolder] = useState(false)
    const [newFolderName, setNewFolderName] = useState("")

    const createFolder = useCreateFolder()
    const subscribe = useSubscribeCatalogFeedMutation()
    const isSubmitting = createFolder.isPending || subscribe.isPending

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault()

        if (!isCreatingFolder && !selectedFolderId) {
            toast.error("Please select a folder")
            return
        }
        if (isCreatingFolder && !newFolderName.trim()) {
            toast.error("Please enter a folder name")
            return
        }

        try {
            let folderId = selectedFolderId

            if (isCreatingFolder) {
                const folder = await createFolder.mutateAsync({
                    name: newFolderName.trim(),
                })
                folderId = folder.id
            }

            await subscribe.mutateAsync({ feedId: feed.id, folderId })
            toast.success(`Subscribed to ${source.name}`)
            onClose()
        } catch (error) {
            if (error instanceof ApiError && error.status === 429) return
            const message =
                (error as { message?: string; detail?: string })?.message ||
                (error as { message?: string; detail?: string })?.detail ||
                "Could not subscribe"
            toast.error(message)
        }
    }

    return (
        <Dialog
            open
            onOpenChange={(open) => {
                if (!open && !isSubmitting) onClose()
            }}
        >
            <DialogContent className="max-h-[90vh] max-w-[95vw] overflow-y-auto sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Rss className="h-5 w-5 text-orange-500" />
                        Subscribe to {source.name}
                    </DialogTitle>
                    <DialogDescription
                        className="text-left break-all"
                        title={feed.feed_url}
                    >
                        {feed.feed_url}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <FolderSelect
                        folders={folders}
                        selectedFolderId={selectedFolderId}
                        onFolderSelect={setSelectedFolderId}
                        isCreatingFolder={isCreatingFolder}
                        onCreateNew={() => {
                            setSelectedFolderId("")
                            setIsCreatingFolder(true)
                            setNewFolderName("")
                        }}
                        onCancelCreate={() => {
                            setIsCreatingFolder(false)
                            setNewFolderName("")
                        }}
                        newFolderName={newFolderName}
                        onNewFolderNameChange={setNewFolderName}
                        isLoading={feedsLoading}
                    />

                    <DialogFooter className="flex-col gap-2 sm:flex-row">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={onClose}
                            disabled={isSubmitting}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting && (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            )}
                            Subscribe
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    )
}
