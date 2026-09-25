"use client"

import { useFeeds, type SubscriptionResponse } from "@infrss/shared"
import { Download, Upload } from "lucide-react"
import Link from "next/link"
import { toast } from "react-hot-toast"

import { Button } from "@/components/ui/button"
import { downloadOPML, generateOPMLContent } from "@/lib/opml-export"
import { SettingsSection } from "./SettingsSection"

export function DataSettings() {
    const { data, isLoading } = useFeeds({})

    const feeds = (data?.subscriptions ?? []) as SubscriptionResponse[]
    const folders = data?.folders ?? []

    const handleExport = () => {
        if (feeds.length === 0) {
            toast.error("No feeds to export")
            return
        }
        try {
            const opml = generateOPMLContent(
                feeds.map((sub) => ({
                    url: sub.feed.url,
                    title: sub.custom_title || sub.feed.title,
                    link: sub.feed.link,
                    folder_id: sub.folder?.id,
                })),
                folders
            )
            downloadOPML(opml)
            toast.success(`Exported ${feeds.length} feeds to OPML`)
        } catch (error) {
            console.error("OPML export error:", error)
            toast.error("Failed to export OPML")
        }
    }

    return (
        <SettingsSection
            title="Feeds & data"
            description="Import or export your subscriptions."
        >
            <div className="flex flex-wrap gap-3">
                <Button asChild variant="outline">
                    <Link href="/import-opml">
                        <Upload />
                        Import OPML
                    </Link>
                </Button>
                <Button
                    variant="outline"
                    onClick={handleExport}
                    disabled={isLoading}
                >
                    <Download />
                    Export OPML
                </Button>
            </div>
        </SettingsSection>
    )
}
