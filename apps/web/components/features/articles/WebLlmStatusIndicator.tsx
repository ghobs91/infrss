"use client"

import { Cpu, HardDrive, Server } from "lucide-react"

import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"

import type { LaymanBackend, LaymanStatus } from "./hooks/use-layman-summary"

interface WebLlmStatusIndicatorProps {
    gpuAvailable: boolean
    backend: LaymanBackend
    status: LaymanStatus
    /** Model load / generation progress, 0–1. */
    progress: number
    /** Optional GPU/JS heap usage in MB. */
    memoryMB?: number
    className?: string
}

const BACKEND_LABEL: Record<Exclude<LaymanBackend, null>, string> = {
    webgpu: "On-device GPU",
    ollama: "Local Ollama",
    server: "Server",
    cache: "Cached",
}

/** Compact indicator of which inference backend is active and its load progress. */
export function WebLlmStatusIndicator({
    gpuAvailable,
    backend,
    status,
    progress,
    memoryMB,
    className,
}: WebLlmStatusIndicatorProps) {
    const percent = Math.round((progress || 0) * 100)
    const label = backend
        ? BACKEND_LABEL[backend]
        : gpuAvailable
          ? "WebGPU ready"
          : "No WebGPU"

    const Icon =
        backend === "server" ? Server : backend === "ollama" ? HardDrive : Cpu

    return (
        <div
            className={cn(
                "flex items-center gap-2 text-[11px] text-muted-foreground",
                className
            )}
            title={`Layman summary backend: ${label}`}
        >
            <Icon className="h-3 w-3 shrink-0" />
            <span className="truncate">
                {status === "generating" && percent > 0
                    ? `${label} · ${percent}%`
                    : label}
            </span>
            {status === "generating" && percent > 0 && (
                <Progress value={percent} className="h-1 w-16" />
            )}
            {typeof memoryMB === "number" && (
                <span className="tabular-nums">{memoryMB} MB</span>
            )}
        </div>
    )
}
