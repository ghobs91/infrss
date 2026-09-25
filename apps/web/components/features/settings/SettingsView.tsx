"use client"

import AppHeader from "@/components/features/navigation/AppHeader"
import { AccountSettings } from "./AccountSettings"
import { AppearanceSettings } from "./AppearanceSettings"
import { DataSettings } from "./DataSettings"
import { DigestSettings } from "./DigestSettings"
import { NewsletterSettings } from "./NewsletterSettings"
import { PlanSettings } from "./PlanSettings"

export function SettingsView() {
    return (
        <div className="flex h-full flex-col">
            <AppHeader
                breadcrumbItems={[{ href: "/settings", label: "Settings" }]}
            />
            <main className="flex-1 overflow-y-auto">
                <div className="mx-auto max-w-3xl space-y-6 px-4 py-6 md:px-6 md:py-8">
                    <header>
                        <h1 className="text-2xl font-bold sm:text-3xl">
                            Settings
                        </h1>
                        <p className="text-muted-foreground">
                            Manage your account, reading experience, and data.
                        </p>
                    </header>

                    <AppearanceSettings />
                    <PlanSettings />
                    <DigestSettings />
                    <NewsletterSettings />
                    <DataSettings />
                    <AccountSettings />
                </div>
            </main>
        </div>
    )
}
