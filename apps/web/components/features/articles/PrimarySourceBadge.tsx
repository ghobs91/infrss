import { ShieldCheck } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

/**
 * Marks a feed/article as coming from a verified primary source (promoted from the catalog).
 */
export function PrimarySourceBadge({ className }: { className?: string }) {
    return (
        <Badge
            variant="success"
            className={cn("gap-1 font-medium", className)}
            title="Verified primary source"
        >
            <ShieldCheck className="h-3 w-3" />
            Primary source
        </Badge>
    )
}
