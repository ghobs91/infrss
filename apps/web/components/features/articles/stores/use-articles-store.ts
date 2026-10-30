import { create } from "zustand"

interface ArticlesState {
    // View State
    viewMode: "list" | "content"
    selectedArticleId: string | null
    showUnreadOnly: boolean
    sidebarOpen: boolean
    /**
     * Articles auto-marked read while scrolling, keyed by id. The unread-only filter keeps
     * these visible (dimmed) for the current session so marking them doesn't remove a row
     * mid-scroll and shift the list; a context change or unmount clears them.
     */
    autoReadIds: Record<string, true>

    // Actions
    setViewMode: (mode: "list" | "content") => void
    selectArticle: (articleId: string | null) => void
    toggleUnreadFilter: () => void
    setSidebarOpen: (isOpen: boolean) => void
    addAutoReadIds: (articleIds: string[]) => void
    clearAutoReadIds: () => void
    reset: () => void
}

export const useArticlesStore = create<ArticlesState>((set) => ({
    viewMode: "list",
    selectedArticleId: null,
    showUnreadOnly: true,
    sidebarOpen: true,
    autoReadIds: {},

    setViewMode: (mode) => set({ viewMode: mode }),
    selectArticle: (articleId) =>
        set((state) => ({
            selectedArticleId: articleId,
            // On mobile, selecting an article should switch to content view
            viewMode: articleId ? "content" : state.viewMode,
        })),
    toggleUnreadFilter: () =>
        set((state) => ({ showUnreadOnly: !state.showUnreadOnly })),
    setSidebarOpen: (isOpen) => set({ sidebarOpen: isOpen }),
    addAutoReadIds: (articleIds) =>
        set((state) => {
            if (articleIds.length === 0) return state
            const autoReadIds = { ...state.autoReadIds }
            for (const id of articleIds) autoReadIds[id] = true
            return { autoReadIds }
        }),
    clearAutoReadIds: () => set({ autoReadIds: {} }),
    reset: () =>
        set({
            viewMode: "list",
            selectedArticleId: null,
            showUnreadOnly: true,
            sidebarOpen: true,
            autoReadIds: {},
        }),
}))
