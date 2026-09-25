"use client"

import { UserRole, useUserLimits } from "@infrss/shared"
import { Sparkles } from "lucide-react"

import { SubscribeButton } from "@/components/billing/SubscribeButton"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { env } from "@/env"
import { SettingsSection } from "./SettingsSection"

const ROLE_LABELS: Record<UserRole, string> = {
    [UserRole.BASIC]: "Basic",
    [UserRole.PRO]: "Pro",
    [UserRole.ADMIN]: "Admin",
}

/** Renders "used of limit"; -1 means the resource is unlimited. */
function formatQuota(used: number, limit: number): string {
    return limit === -1 ? `${used} · unlimited` : `${used} / ${limit}`
}

function UsageRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex items-center justify-between gap-4 py-2 text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium tabular-nums">{value}</span>
        </div>
    )
}

export function PlanSettings() {
    const { data: limits, isLoading } = useUserLimits()

    const role = limits?.role
    const isPaid = role === UserRole.PRO || role === UserRole.ADMIN
    const monthlyUrl = env.NEXT_PUBLIC_POLAR_MONTHLY_CHECKOUT_URL
    const yearlyUrl = env.NEXT_PUBLIC_POLAR_YEARLY_CHECKOUT_URL

    const codexUsage = limits?.usage.codex
    const codexValue = codexUsage
        ? "unlimited" in codexUsage
            ? "Unlimited"
            : codexUsage.period === "month"
              ? `${codexUsage.used} / ${codexUsage.limit} per month`
              : `${codexUsage.used} / ${codexUsage.limit} per ${codexUsage.window_hours ?? 24}h`
        : null

    return (
        <SettingsSection
            title="Plan & usage"
            description="Your current plan and how much of it you've used."
        >
            {isLoading || !limits ? (
                <div className="space-y-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className="h-5 w-full" />
                    ))}
                </div>
            ) : (
                <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-3">
                        <Badge
                            variant={isPaid ? "orange" : "secondary"}
                            className="gap-1"
                        >
                            {isPaid ? <Sparkles className="size-3" /> : null}
                            {ROLE_LABELS[limits.role]}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                            {isPaid
                                ? "Thanks for supporting Infrss."
                                : "Upgrade for higher limits and AI features."}
                        </span>
                    </div>

                    {!isPaid && monthlyUrl ? (
                        <div className="flex flex-wrap gap-3">
                            <SubscribeButton checkoutUrl={monthlyUrl}>
                                Upgrade monthly
                            </SubscribeButton>
                            {yearlyUrl ? (
                                <SubscribeButton
                                    checkoutUrl={yearlyUrl}
                                    className="bg-secondary text-secondary-foreground hover:bg-secondary/80"
                                >
                                    Upgrade yearly
                                </SubscribeButton>
                            ) : null}
                        </div>
                    ) : null}

                    <div className="divide-y divide-border/60 border-t border-border/60">
                        <UsageRow
                            label="Feeds"
                            value={formatQuota(
                                limits.usage.subscriptions,
                                limits.limits.max_subscriptions
                            )}
                        />
                        <UsageRow
                            label="Saved articles"
                            value={formatQuota(
                                limits.usage.saved_articles,
                                limits.limits.max_saved_articles
                            )}
                        />
                        <UsageRow
                            label="AI calls today"
                            value={formatQuota(
                                limits.usage.daily_ai_calls,
                                limits.limits.max_daily_ai_calls
                            )}
                        />
                        <UsageRow
                            label="Full-text scrapes today"
                            value={formatQuota(
                                limits.usage.daily_scrapes,
                                limits.limits.max_daily_scrapes
                            )}
                        />
                        {codexValue ? (
                            <UsageRow label="Daily Digest" value={codexValue} />
                        ) : null}
                        <UsageRow
                            label="Semantic search"
                            value={
                                limits.limits.semantic_search
                                    ? "Enabled"
                                    : "Not included"
                            }
                        />
                    </div>
                </div>
            )}
        </SettingsSection>
    )
}
