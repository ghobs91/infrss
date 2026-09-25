"use client"

import { Check, Copy } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "react-hot-toast"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiClient } from "@/lib/api-client"
import { isCloudProd } from "@/lib/is-cloud-prod"
import { SettingsSection } from "./SettingsSection"

/**
 * The user's private inbound email alias for subscribing to newsletters. Inbound email is
 * handled by the hosted worker, so this section only appears on the cloud deployment.
 */
export function NewsletterSettings() {
    const isCloud = isCloudProd()
    const [tokenData, setTokenData] = useState<{
        token: string
        email: string
    } | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [copied, setCopied] = useState(false)

    useEffect(() => {
        if (!isCloud) return
        let cancelled = false

        setIsLoading(true)
        ApiClient.getNewsletterToken()
            .then((response) => {
                if (!cancelled) setTokenData(response)
            })
            .catch(() => {
                if (!cancelled) {
                    toast.error("Failed to load your newsletter address.")
                }
            })
            .finally(() => {
                if (!cancelled) setIsLoading(false)
            })

        return () => {
            cancelled = true
        }
    }, [isCloud])

    if (!isCloud) return null

    const copyToClipboard = () => {
        if (!tokenData?.email) return
        navigator.clipboard.writeText(tokenData.email)
        setCopied(true)
        toast.success("Copied to clipboard")
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <SettingsSection
            title="Newsletters"
            description="Subscribe to mailing lists with your private email address."
        >
            {isLoading ? (
                <Skeleton className="h-10 w-full" />
            ) : (
                <div className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/40 p-2 pl-3">
                    <span className="min-w-0 flex-1 truncate font-mono text-xs font-semibold">
                        {tokenData?.email || "Unavailable"}
                    </span>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={copyToClipboard}
                        disabled={!tokenData}
                        aria-label="Copy newsletter address"
                    >
                        {copied ? <Check /> : <Copy />}
                    </Button>
                </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
                Paste this address wherever you&apos;d subscribe to a
                publication. The first email creates the feed in your
                Newsletters folder.
            </p>
        </SettingsSection>
    )
}
