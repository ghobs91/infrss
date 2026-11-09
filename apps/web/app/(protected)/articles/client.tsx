"use client"

import { useMemo } from "react"
import { useInfiniteArticles } from "@infrss/shared"
import { ArticlesView } from "@/components/features/articles/ArticlesView"
import { useArticlesStore } from "@/components/features/articles/stores/use-articles-store"
import type { Article } from "@infrss/shared"

interface ArticlesPageClientProps {
    defaultLayout?: number[]
}

export function ArticlesPageClient({ defaultLayout }: ArticlesPageClientProps) {
    const showUnreadOnly = useArticlesStore((state) => state.showUnreadOnly)
    const query = useInfiniteArticles(
        {
            limit: 25,
            isRead: showUnreadOnly ? false : undefined,
        },
        {
            staleTime: 5 * 60 * 1000, // 5 minutes
        }
    )

    const articles = useMemo(() => {
        if (!query.data?.pages) return []
        return query.data.pages.flatMap(
            (page: { items: unknown[] }) => page.items
        ) as Article[]
    }, [query.data])

    return (
        <ArticlesView
            initialSidebarTitle="All Articles"
            defaultLayout={defaultLayout}
            articles={articles}
            query={query}
        />
    )
}
