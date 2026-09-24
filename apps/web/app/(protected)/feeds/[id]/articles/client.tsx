"use client"

import { useMemo } from "react"
import { useInfiniteArticles } from "@infrss/shared"
import { ArticlesView } from "@/components/features/articles/ArticlesView"
import type { Article } from "@infrss/shared"

interface FeedArticlesPageClientProps {
    feedId: string
    defaultLayout?: number[]
}

export function FeedArticlesPageClient({
    feedId,
    defaultLayout,
}: FeedArticlesPageClientProps) {
    const query = useInfiniteArticles(
        {
            feedId,
            limit: 25,
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
            feedId={feedId}
            defaultLayout={defaultLayout}
            articles={articles}
            query={query}
        />
    )
}
