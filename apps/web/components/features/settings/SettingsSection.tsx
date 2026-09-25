import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface SettingsSectionProps {
    title: string
    description?: string
    children: React.ReactNode
    className?: string
    contentClassName?: string
}

/**
 * Consistent card shell for a single settings group. Keeps every section on the
 * settings page using the same heading/spacing rhythm.
 */
export function SettingsSection({
    title,
    description,
    children,
    className,
    contentClassName,
}: SettingsSectionProps) {
    return (
        <Card className={cn("shadow-none", className)}>
            <CardHeader>
                <CardTitle className="text-lg">{title}</CardTitle>
                {description ? (
                    <CardDescription>{description}</CardDescription>
                ) : null}
            </CardHeader>
            <CardContent className={contentClassName}>{children}</CardContent>
        </Card>
    )
}
