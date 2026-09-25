"use client"

import { Monitor, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { SettingsSection } from "./SettingsSection"

const THEME_OPTIONS = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
] as const

export function AppearanceSettings() {
    const { theme, setTheme } = useTheme()
    // next-themes can't know the resolved theme until after hydration.
    const [mounted, setMounted] = useState(false)

    useEffect(() => setMounted(true), [])

    return (
        <SettingsSection
            title="Appearance"
            description="Choose how Infrss looks on this device."
        >
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {THEME_OPTIONS.map((option) => {
                    const active = mounted && theme === option.value
                    return (
                        <Button
                            key={option.value}
                            type="button"
                            variant="outline"
                            onClick={() => setTheme(option.value)}
                            aria-pressed={active}
                            className={cn(
                                "flex h-auto flex-col items-start gap-2 p-4",
                                active && "border-primary ring-1 ring-primary"
                            )}
                        >
                            <option.icon />
                            <span className="text-sm font-medium">
                                {option.label}
                            </span>
                        </Button>
                    )
                })}
            </div>
        </SettingsSection>
    )
}
