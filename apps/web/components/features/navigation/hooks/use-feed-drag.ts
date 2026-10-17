"use client"

import {
    PointerSensor,
    closestCenter,
    useSensor,
    useSensors,
    type DragEndEvent,
    type DragStartEvent,
} from "@dnd-kit/core"
import { useUpdateFeed } from "@infrss/shared"
import { useCallback, useState } from "react"
import toast from "react-hot-toast"

/** Payload carried by a draggable feed row. */
export interface FeedDragData {
    feedId: string
    title: string
    image?: string
    /** Folder the feed currently lives in (null = unfiled). */
    folderId: string | null
}

/** Payload carried by a folder drop target. */
export interface FolderDropData {
    folderId: string
}

export interface ActiveDragFeed {
    title: string
    image?: string
}

/**
 * Drag-and-drop wiring for moving feeds between folders in the sidebar.
 *
 * Returns the sensor config, collision detection and the DndContext event handlers. The caller
 * renders `<DndContext {...}>` around the feed list and a `<DragOverlay>` using `activeFeed`.
 * The pointer sensor only activates after a small movement so a plain click still navigates.
 */
export function useFeedDrag() {
    const updateFeed = useUpdateFeed()
    const [activeFeed, setActiveFeed] = useState<ActiveDragFeed | null>(null)

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
    )

    const handleDragStart = useCallback((event: DragStartEvent) => {
        const data = event.active.data.current as FeedDragData | undefined
        if (data) {
            setActiveFeed({ title: data.title, image: data.image })
        }
    }, [])

    const handleDragCancel = useCallback(() => setActiveFeed(null), [])

    const handleDragEnd = useCallback(
        (event: DragEndEvent) => {
            setActiveFeed(null)
            const { active, over } = event
            if (!over) return

            const source = active.data.current as FeedDragData | undefined
            const target = over.data.current as FolderDropData | undefined
            if (!source || !target) return
            // Dropping a feed back on its own folder is a no-op.
            if (source.folderId === target.folderId) return

            toast.promise(
                updateFeed.mutateAsync({
                    feedId: source.feedId,
                    data: { folder_id: target.folderId },
                }),
                {
                    loading: "Moving feed…",
                    success: "Feed moved",
                    error: "Could not move feed",
                }
            )
        },
        [updateFeed]
    )

    return {
        sensors,
        collisionDetection: closestCenter,
        activeFeed,
        handleDragStart,
        handleDragEnd,
        handleDragCancel,
    }
}
