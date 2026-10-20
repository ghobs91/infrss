import { useProfile } from "@infrss/shared"

export function useUserRole() {
    const {
        data: profile,
        isLoading,
        error,
    } = useProfile({
        retry: false,
        staleTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
    })

    return {
        profile,
        isAdmin: profile?.role === "ADMIN",
        isLoading,
        error,
    }
}
