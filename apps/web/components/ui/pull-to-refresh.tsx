"use client"

import { cn } from "@/lib/utils"
import { RefreshCw } from "lucide-react"
import {
    useEffect,
    useRef,
    useState,
    type ReactNode,
    type RefObject,
} from "react"

/** Pull distance (after resistance) that arms a refresh. */
const REFRESH_THRESHOLD = 64
const MAX_PULL = 92
const RESISTANCE = 0.55
/** Resting offset of the indicator while a refresh is running. */
const INDICATOR_OFFSET = 56

interface PullToRefreshProps {
    /** The scrollable element to watch. */
    scrollRef: RefObject<HTMLElement | null>
    onRefresh: () => void | Promise<void>
    enabled?: boolean
    className?: string
    children: ReactNode
}

/**
 * Touch pull-to-refresh for the mobile article list.
 *
 * Uses native (non-passive) touch listeners so a downward drag at scrollTop 0 can be claimed
 * from iOS Safari's rubber-band, then renders a floating Liquid Glass indicator above the
 * list. Desktop is untouched: `enabled` is false there and no listeners are attached.
 */
export function PullToRefresh({
    scrollRef,
    onRefresh,
    enabled = true,
    className,
    children,
}: PullToRefreshProps) {
    const [pull, setPull] = useState(0)
    const [isDragging, setIsDragging] = useState(false)
    const [isRefreshing, setIsRefreshing] = useState(false)

    const pullRef = useRef(0)
    const startYRef = useRef(0)
    const startXRef = useRef(0)
    const trackingRef = useRef(false)
    const refreshingRef = useRef(false)
    const onRefreshRef = useRef(onRefresh)

    useEffect(() => {
        onRefreshRef.current = onRefresh
    }, [onRefresh])

    useEffect(() => {
        const element = scrollRef.current
        if (!enabled || !element) return

        const reset = () => {
            trackingRef.current = false
            setIsDragging(false)
            pullRef.current = 0
            setPull(0)
        }

        const handleTouchStart = (event: TouchEvent) => {
            if (refreshingRef.current || event.touches.length !== 1) return
            if (element.scrollTop > 0) return

            const touch = event.touches[0]
            if (!touch) return
            startYRef.current = touch.clientY
            startXRef.current = touch.clientX
            trackingRef.current = true
            setIsDragging(true)
        }

        const handleTouchMove = (event: TouchEvent) => {
            if (!trackingRef.current || refreshingRef.current) return
            const touch = event.touches[0]
            if (!touch) return

            const deltaY = touch.clientY - startYRef.current
            const deltaX = touch.clientX - startXRef.current

            // A horizontal gesture (swipe-back, carousel) belongs to someone else.
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 8) {
                reset()
                return
            }

            if (deltaY <= 0 || element.scrollTop > 0) {
                if (pullRef.current !== 0) {
                    pullRef.current = 0
                    setPull(0)
                }
                return
            }

            // Claim the gesture so the page doesn't rubber-band underneath it.
            if (event.cancelable) event.preventDefault()

            const next = Math.min(MAX_PULL, deltaY * RESISTANCE)
            pullRef.current = next
            setPull(next)
        }

        const handleTouchEnd = async () => {
            if (!trackingRef.current) return
            trackingRef.current = false
            setIsDragging(false)

            if (pullRef.current < REFRESH_THRESHOLD) {
                pullRef.current = 0
                setPull(0)
                return
            }

            refreshingRef.current = true
            setIsRefreshing(true)
            pullRef.current = INDICATOR_OFFSET
            setPull(INDICATOR_OFFSET)

            try {
                await onRefreshRef.current()
            } catch (error) {
                console.error("Pull-to-refresh failed:", error)
            } finally {
                refreshingRef.current = false
                setIsRefreshing(false)
                pullRef.current = 0
                setPull(0)
            }
        }

        element.addEventListener("touchstart", handleTouchStart, {
            passive: true,
        })
        element.addEventListener("touchmove", handleTouchMove, {
            passive: false,
        })
        element.addEventListener("touchend", handleTouchEnd)
        element.addEventListener("touchcancel", reset)

        return () => {
            element.removeEventListener("touchstart", handleTouchStart)
            element.removeEventListener("touchmove", handleTouchMove)
            element.removeEventListener("touchend", handleTouchEnd)
            element.removeEventListener("touchcancel", reset)
        }
    }, [enabled, scrollRef])

    const armed = pull >= REFRESH_THRESHOLD
    const progress = Math.min(pull / REFRESH_THRESHOLD, 1)

    return (
        <div className={cn("relative h-full overflow-hidden", className)}>
            <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-x-0 top-2 z-20 flex justify-center"
                style={{
                    opacity: isRefreshing ? 1 : progress,
                    transform: `translateY(${pull - INDICATOR_OFFSET}px)`,
                    transition: isDragging
                        ? "none"
                        : "transform 220ms cubic-bezier(0.2, 0.9, 0.2, 1), opacity 200ms ease",
                }}
            >
                <div className="glass-control flex h-9 w-9 items-center justify-center rounded-full shadow-lg">
                    <RefreshCw
                        className={cn(
                            "h-4 w-4 text-muted-foreground",
                            isRefreshing && "animate-spin"
                        )}
                        style={
                            isRefreshing
                                ? undefined
                                : {
                                      transform: `rotate(${progress * 180}deg)`,
                                      color: armed
                                          ? "hsl(var(--secondary))"
                                          : undefined,
                                  }
                        }
                    />
                </div>
            </div>
            <span className="sr-only" role="status">
                {isRefreshing ? "Refreshing feeds" : ""}
            </span>
            {children}
        </div>
    )
}
