import { QueryProvider } from "@/components/providers/QueryProvider"
import { Metadata, Viewport } from "next"
import {
    eb_garamond,
    instrumentSerif,
    geistMono,
    geistSans,
    logo,
    notoSerifJP,
    notoSerifSC,
    notoSerifTC,
} from "@/lib/fonts"
import "./globals.css"
import { PosthogProvider } from "@/components/providers/PosthogProvider"
import { cn } from "@/lib/utils"

const baseUrl = process.env.NEXT_PUBLIC_APP_URL || "https://app.readspace.ai"

export const metadata: Metadata = {
    title: "Infrss | A calm inbox for your reading",
    description:
        "All your reading in one place — a privacy-friendly inbox for RSS, newsletters, threads, and books. Open-source, distraction-free, and self-hostable.",
    metadataBase: new URL(baseUrl),
    generator: "Next.js",
    applicationName: "Infrss",
    referrer: "origin-when-cross-origin",
    keywords: [
        "RSS reader",
        "newsletter inbox",
        "reading app",
        "privacy-first",
        "open source",
        "self-hosted",
        "distraction-free reading",
        "content aggregation",
        "Twitter threads",
        "Reddit posts",
        "book reading",
        "calm reading",
    ],
    authors: [{ name: "Infrss Team" }],
    creator: "Infrss",
    publisher: "Infrss",
    formatDetection: {
        email: false,
        telephone: false,
        address: false,
    },
    icons: {
        icon: [
            { url: "/favicon.ico", sizes: "any" },
            { url: "/icon.svg", type: "image/svg+xml" },
        ],
        apple: [{ url: "/apple-touch-icon.png" }],
    },
    openGraph: {
        title: "Infrss | A calm inbox for your reading",
        description:
            "All your reading in one place — a privacy-friendly inbox for RSS, newsletters, threads, and books. Open-source, distraction-free, and self-hostable.",
        url: baseUrl,
        siteName: "Infrss",
        locale: "en_US",
        type: "website",
    },
    twitter: {
        card: "summary",
        title: "Infrss | A calm inbox for your reading",
        description:
            "All your reading in one place — a privacy-friendly inbox for RSS, newsletters, threads, and books. Open-source, distraction-free, and self-hostable.",
        creator: "@infrss_ai",
    },
    robots: {
        index: true,
        follow: true,
        googleBot: {
            index: true,
            follow: true,
            "max-video-preview": -1,
            "max-image-preview": "large",
            "max-snippet": -1,
        },
    },
}

// Define viewport settings
export const viewport: Viewport = {
    themeColor: "#6A994E",
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
}

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body
                className={cn(
                    geistSans.variable,
                    geistMono.variable,
                    eb_garamond.variable,
                    instrumentSerif.variable,
                    logo.variable,
                    notoSerifSC.variable,
                    notoSerifJP.variable,
                    notoSerifTC.variable,
                    "font-sans antialiased mt-0"
                )}
            >
                <PosthogProvider>
                    <QueryProvider>
                        <main className="w-full">{children}</main>
                    </QueryProvider>
                </PosthogProvider>
            </body>
        </html>
    )
}
