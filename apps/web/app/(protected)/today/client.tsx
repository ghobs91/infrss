"use client"

import { useMemo } from "react"
import { useInfiniteTodayArticles, ArticleFilterMode } from "@infrss/shared"
import { ArticlesView } from "@/components/features/articles/ArticlesView"
import { useArticlesStore } from "@/components/features/articles/stores/use-articles-store"
import type { Article } from "@infrss/shared"

interface TodayPageClientProps {
    defaultLayout?: number[]
}

export function TodayPageClient({ defaultLayout }: TodayPageClientProps) {
    const showUnreadOnly = useArticlesStore((state) => state.showUnreadOnly)
    const query = useInfiniteTodayArticles({
        limit: 25,
        isRead: showUnreadOnly ? false : undefined,
    })

    const articles = useMemo(() => {
        if (!query.data?.pages) return []
        return query.data.pages.flatMap(
            (page: { items: unknown[] }) => page.items
        ) as Article[]
    }, [query.data])

    return (
        <ArticlesView
            initialSidebarTitle="Today"
            mode={ArticleFilterMode.Today}
            defaultLayout={defaultLayout}
            articles={articles}
            query={query}
        />
    )
}
