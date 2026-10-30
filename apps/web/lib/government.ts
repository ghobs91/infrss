import type { CatalogSource } from "@infrss/shared"
import {
    Atom,
    Briefcase,
    Building2,
    Car,
    Coins,
    GraduationCap,
    Globe,
    HardHat,
    Heart,
    Leaf,
    MoreHorizontal,
    Scale,
    Train,
    type LucideIcon,
} from "lucide-react"

import { US_STATES, type UsState } from "./us-zip"

export type GovernmentLevel = "federal" | "state" | "local" | "international"

export const GOVERNMENT_LEVEL_LABELS: Record<GovernmentLevel, string> = {
    federal: "Federal",
    state: "State",
    local: "Local",
    international: "International",
}

export interface GovernmentDepartmentConfig {
    id: string
    label: string
    icon: LucideIcon
    keywords: string[]
}

/**
 * Department buckets for government sources. Ordered by the classifier below: earlier entries
 * win, so "Transit" is checked before the broader "Transportation" bucket. The labels are used
 * verbatim in the catalog and sorted alphabetically at render time.
 */
export const GOVERNMENT_DEPARTMENTS: GovernmentDepartmentConfig[] = [
    {
        id: "transit",
        label: "Transit Agencies",
        icon: Train,
        keywords: [
            "transit",
            "metro",
            "mta",
            "rail",
            "railroad",
            "bus",
            "port authority",
            "airport",
            "transportation authority",
            "mobility",
            "ferry",
        ],
    },
    {
        id: "transportation",
        label: "Transportation Department",
        icon: Car,
        keywords: [
            "transportation",
            "highway",
            "motor vehicle",
            "dmv",
            "aviation",
            "traffic",
            "roads",
            "infrastructure",
        ],
    },
    {
        id: "health",
        label: "Health & Human Services",
        icon: Heart,
        keywords: [
            "health",
            "human services",
            "medicaid",
            "medicare",
            "cdc",
            "national institutes of health",
            "food and drug",
            "hospital",
            "disease",
            "behavioral",
            "public health",
        ],
    },
    {
        id: "commerce",
        label: "Commerce & Economics",
        icon: Briefcase,
        keywords: [
            "commerce",
            "economic development",
            "economics",
            "trade",
            "small business",
            "business development",
            "enterprise",
        ],
    },
    {
        id: "finance",
        label: "Finance & Economy",
        icon: Coins,
        keywords: [
            "finance",
            "financial",
            "treasury",
            "tax",
            "revenue",
            "budget",
            "fiscal",
            "comptroller",
            "controller",
            "auditor",
            "banking",
            "insurance",
            "securities",
            "currency",
            "retirement system",
        ],
    },
    {
        id: "science",
        label: "Science, Space & Energy",
        icon: Atom,
        keywords: [
            "science",
            "space",
            "energy",
            "nasa",
            "nuclear",
            "research",
            "technology",
            "innovation",
            "communications",
            "broadband",
            "geological",
        ],
    },
    {
        id: "environment",
        label: "Environment, Agriculture & Natural Resources",
        icon: Leaf,
        keywords: [
            "environment",
            "agricultur",
            "natural resources",
            "wildlife",
            "fish",
            "forest",
            "park",
            "water",
            "conservation",
            "climate",
            "land management",
            "recreation",
        ],
    },
    {
        id: "justice",
        label: "Justice, Courts & Public Safety",
        icon: Scale,
        keywords: [
            "justice",
            "court",
            "judicial",
            "law enforcement",
            "police",
            "sheriff",
            "correction",
            "attorney",
            "legal",
            "public safety",
            "fire",
            "emergency management",
            "homeland security",
        ],
    },
    {
        id: "labor",
        label: "Labor & Workforce",
        icon: HardHat,
        keywords: [
            "labor",
            "workforce",
            "employment",
            "unemployment",
            "workers",
            "industrial relations",
        ],
    },
    {
        id: "education",
        label: "Education",
        icon: GraduationCap,
        keywords: [
            "education",
            "school",
            "university",
            "college",
            "library",
            "student",
            "academy",
        ],
    },
    {
        id: "international",
        label: "International Affairs",
        icon: Globe,
        keywords: [
            "international",
            "foreign",
            "embassy",
            "diplomatic",
            "global affairs",
            "department of state",
            "state department",
        ],
    },
    {
        id: "state-local",
        label: "State & Local Government",
        icon: Building2,
        keywords: [
            "state of ",
            "county",
            "city of",
            "municipal",
            "township",
            "borough",
            "parish",
            "village",
            "governor",
            "legislature",
            "council",
            "assembly",
        ],
    },
]

const OTHER_DEPARTMENT: GovernmentDepartmentConfig = {
    id: "other",
    label: "Other Agencies",
    icon: MoreHorizontal,
    keywords: [],
}

const LOCAL_PATTERNS = [
    "city of ",
    "new york city",
    "nyc",
    "county",
    "municipal",
    "township",
    "borough",
    "parish",
    "village of ",
    "school district",
    "public schools",
    "port authority",
    "transit authority",
    "transportation authority",
    "metro",
    "mta",
    "mayor",
    "comptroller",
]

const STATE_SUFFIXES = US_STATES.map((state) => ({
    ...state,
    name: state.name.toLowerCase(),
})).sort((a, b) => b.name.length - a.name.length)

/** Source is a government entity, either by catalog type or an unambiguous .gov/.mil domain. */
export function isGovernmentSource(source: CatalogSource): boolean {
    if (
        source.entity_type === "GOV_FEDERAL" ||
        source.entity_type === "GOV_STATE"
    ) {
        return true
    }
    const domain = source.canonical_domain.toLowerCase()
    return (
        domain.endsWith(".gov") ||
        domain.endsWith(".mil") ||
        domain.endsWith(".us")
    )
}

/**
 * Best-effort level for a government source. Federal Register entities carry `jurisdiction="US"`;
 * state sources usually carry `US-XX` (or a state name in the entity name/domain); municipal
 * sources are detected by common local-government naming patterns.
 */
export function governmentLevelFor(source: CatalogSource): GovernmentLevel {
    const jurisdiction = (source.jurisdiction ?? "").toUpperCase()
    if (jurisdiction === "US") return "federal"
    if (jurisdiction.startsWith("US-")) return "state"

    const haystack = `${source.name} ${source.canonical_domain}`.toLowerCase()
    // Check municipal naming before the GOV_STATE fallback: the catalog uses GOV_STATE for both
    // state agencies and city/county sources, so entity type alone cannot distinguish them.
    if (LOCAL_PATTERNS.some((pattern) => haystack.includes(pattern))) {
        return "local"
    }
    if (source.entity_type === "GOV_STATE") return "state"
    if (findStateInText(haystack)) return "state"

    const domain = source.canonical_domain.toLowerCase()
    if (
        domain.endsWith(".gov") ||
        domain.endsWith(".mil") ||
        domain.endsWith(".us")
    ) {
        return "federal"
    }
    return "international"
}

/** True when the source is the user's own state or a local government inside that state. */
export function sourceMatchesState(
    source: CatalogSource,
    state: UsState
): boolean {
    const jurisdiction = (source.jurisdiction ?? "").toUpperCase()
    if (jurisdiction === `US-${state.code}`) return true

    const domain = source.canonical_domain.toLowerCase()
    const code = state.code.toLowerCase()
    if (domain.endsWith(`.${code}.us`) || domain.endsWith(`.${code}.gov`)) {
        return true
    }
    // NYC agencies live on .nyc.gov rather than .ny.gov.
    if (state.code === "NY" && domain.endsWith(".nyc.gov")) return true

    const haystack = `${source.name} ${domain}`.toLowerCase()
    if (state.code === "NY" && haystack.includes("nyc")) return true
    if (findSpecificState(haystack, state)) return true

    return false
}

function findSpecificState(haystack: string, state: UsState): boolean {
    const name = state.name.toLowerCase()
    if (!haystack.includes(name)) return false
    // "Virginia" must not match "West Virginia": require that no longer state name containing
    // this name also matches at the same position.
    for (const candidate of STATE_SUFFIXES) {
        if (candidate.name.length <= name.length) break
        if (
            candidate.name.includes(name) &&
            haystack.includes(candidate.name)
        ) {
            return false
        }
    }
    return true
}

function findStateInText(haystack: string): UsState | null {
    for (const state of STATE_SUFFIXES) {
        if (haystack.includes(state.name)) return state
    }
    return null
}

/** Department bucket for a government source, falling back to "Other Agencies". */
export function governmentDepartmentFor(
    source: CatalogSource
): GovernmentDepartmentConfig {
    const haystack = `${source.name} ${source.canonical_domain}`.toLowerCase()
    for (const department of GOVERNMENT_DEPARTMENTS) {
        if (department.keywords.some((keyword) => haystack.includes(keyword))) {
            return department
        }
    }
    return OTHER_DEPARTMENT
}

export interface GovernmentDepartmentGroup {
    id: string
    label: string
    icon: LucideIcon
    sources: CatalogSource[]
}

/**
 * Group government sources by department. Real departments sort alphabetically; "Other Agencies"
 * is kept last as a catch-all rather than appearing mid-list at "O".
 */
export function groupGovernmentSources(
    sources: CatalogSource[]
): GovernmentDepartmentGroup[] {
    const groups = new Map<string, GovernmentDepartmentGroup>()
    for (const source of sources) {
        const department = governmentDepartmentFor(source)
        const existing = groups.get(department.id)
        if (existing) {
            existing.sources.push(source)
        } else {
            groups.set(department.id, {
                id: department.id,
                label: department.label,
                icon: department.icon,
                sources: [source],
            })
        }
    }

    for (const group of groups.values()) {
        group.sources.sort((a, b) => a.name.localeCompare(b.name))
    }

    return [...groups.values()].sort((a, b) => {
        if (a.id === "other") return 1
        if (b.id === "other") return -1
        return a.label.localeCompare(b.label)
    })
}
