"use client"

import { useDeleteAccount } from "@infrss/shared"
import { LogOut, Trash2 } from "lucide-react"
import { useState } from "react"
import { toast } from "react-hot-toast"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { useCurrentUser } from "@/hooks/use-current-user"
import { createClient } from "@/lib/supabase/client"
import { SettingsSection } from "./SettingsSection"

export function AccountSettings() {
    const { user } = useCurrentUser()
    const deleteAccount = useDeleteAccount()
    const [confirmOpen, setConfirmOpen] = useState(false)

    const name =
        user?.user_metadata?.full_name ||
        user?.user_metadata?.display_name ||
        null
    const email = user?.email || null
    const avatar = user?.user_metadata?.avatar_url

    const handleSignOut = async () => {
        const supabase = createClient()
        await supabase.auth.signOut({ scope: "local" })
        window.location.href = "/login"
    }

    const handleDeleteAccount = async () => {
        try {
            await toast.promise(deleteAccount.mutateAsync(), {
                loading: "Deleting your account…",
                success: "Your account has been deleted",
                error: "Couldn't delete your account",
            })
            const supabase = createClient()
            await supabase.auth.signOut({ scope: "local" })
            window.location.href = "/login"
        } catch {
            // toast.promise already surfaced the error
        }
    }

    return (
        <SettingsSection
            title="Account"
            description="Manage the account you use to sign in to Infrss."
        >
            <div className="flex flex-col gap-6">
                <div className="flex items-center gap-4">
                    <Avatar className="h-12 w-12">
                        <AvatarImage src={avatar} alt={name || email || ""} />
                        <AvatarFallback className="bg-muted text-muted-foreground">
                            {(name || email || "?").charAt(0).toUpperCase()}
                        </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                        <p className="truncate font-medium">
                            {name || "Your account"}
                        </p>
                        <p className="truncate text-sm text-muted-foreground">
                            {email}
                        </p>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 border-t border-border/60 pt-6">
                    <Button variant="outline" onClick={handleSignOut}>
                        <LogOut />
                        Log out
                    </Button>
                    <Button
                        variant="destructive"
                        onClick={() => setConfirmOpen(true)}
                    >
                        <Trash2 />
                        Delete account
                    </Button>
                </div>
            </div>

            <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            Delete your account?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            This permanently deletes your account, feeds,
                            articles, and saved items. This action cannot be
                            undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleteAccount.isPending}>
                            Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(event) => {
                                event.preventDefault()
                                handleDeleteAccount()
                            }}
                            disabled={deleteAccount.isPending}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleteAccount.isPending
                                ? "Deleting…"
                                : "Delete account"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </SettingsSection>
    )
}
