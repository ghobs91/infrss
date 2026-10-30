export interface UsState {
    code: string
    name: string
}

/** US states, DC, and inhabited territories keyed by their two-letter code. */
export const US_STATES: UsState[] = [
    { code: "AL", name: "Alabama" },
    { code: "AK", name: "Alaska" },
    { code: "AZ", name: "Arizona" },
    { code: "AR", name: "Arkansas" },
    { code: "CA", name: "California" },
    { code: "CO", name: "Colorado" },
    { code: "CT", name: "Connecticut" },
    { code: "DE", name: "Delaware" },
    { code: "DC", name: "District of Columbia" },
    { code: "FL", name: "Florida" },
    { code: "GA", name: "Georgia" },
    { code: "HI", name: "Hawaii" },
    { code: "ID", name: "Idaho" },
    { code: "IL", name: "Illinois" },
    { code: "IN", name: "Indiana" },
    { code: "IA", name: "Iowa" },
    { code: "KS", name: "Kansas" },
    { code: "KY", name: "Kentucky" },
    { code: "LA", name: "Louisiana" },
    { code: "ME", name: "Maine" },
    { code: "MD", name: "Maryland" },
    { code: "MA", name: "Massachusetts" },
    { code: "MI", name: "Michigan" },
    { code: "MN", name: "Minnesota" },
    { code: "MS", name: "Mississippi" },
    { code: "MO", name: "Missouri" },
    { code: "MT", name: "Montana" },
    { code: "NE", name: "Nebraska" },
    { code: "NV", name: "Nevada" },
    { code: "NH", name: "New Hampshire" },
    { code: "NJ", name: "New Jersey" },
    { code: "NM", name: "New Mexico" },
    { code: "NY", name: "New York" },
    { code: "NC", name: "North Carolina" },
    { code: "ND", name: "North Dakota" },
    { code: "OH", name: "Ohio" },
    { code: "OK", name: "Oklahoma" },
    { code: "OR", name: "Oregon" },
    { code: "PA", name: "Pennsylvania" },
    { code: "RI", name: "Rhode Island" },
    { code: "SC", name: "South Carolina" },
    { code: "SD", name: "South Dakota" },
    { code: "TN", name: "Tennessee" },
    { code: "TX", name: "Texas" },
    { code: "UT", name: "Utah" },
    { code: "VT", name: "Vermont" },
    { code: "VA", name: "Virginia" },
    { code: "WA", name: "Washington" },
    { code: "WV", name: "West Virginia" },
    { code: "WI", name: "Wisconsin" },
    { code: "WY", name: "Wyoming" },
    { code: "PR", name: "Puerto Rico" },
    { code: "VI", name: "U.S. Virgin Islands" },
    { code: "GU", name: "Guam" },
]

const STATE_BY_CODE = new Map(US_STATES.map((state) => [state.code, state]))

/**
 * ZIP prefix ranges. The first three digits are allocated geographically by the USPS, so a
 * range lookup resolves a ZIP to its state without shipping the full ~42k-row ZIP database.
 * Texas's 733 prefix is carved out of Oklahoma's 730-749 block (Austin).
 */
const ZIP_RANGES: Array<[number, number, string]> = [
    [5, 5, "NY"],
    [6, 7, "PR"],
    [8, 8, "VI"],
    [9, 9, "PR"],
    [10, 27, "MA"],
    [28, 29, "RI"],
    [30, 38, "NH"],
    [39, 49, "ME"],
    [50, 59, "VT"],
    [60, 69, "CT"],
    [70, 89, "NJ"],
    [100, 149, "NY"],
    [150, 196, "PA"],
    [197, 199, "DE"],
    [200, 205, "DC"],
    [206, 219, "MD"],
    [220, 246, "VA"],
    [247, 268, "WV"],
    [270, 289, "NC"],
    [290, 299, "SC"],
    [300, 319, "GA"],
    [320, 349, "FL"],
    [350, 369, "AL"],
    [370, 385, "TN"],
    [386, 397, "MS"],
    [398, 399, "GA"],
    [400, 427, "KY"],
    [430, 459, "OH"],
    [460, 479, "IN"],
    [480, 499, "MI"],
    [500, 528, "IA"],
    [530, 549, "WI"],
    [550, 567, "MN"],
    [570, 577, "SD"],
    [580, 588, "ND"],
    [590, 599, "MT"],
    [600, 629, "IL"],
    [630, 658, "MO"],
    [660, 679, "KS"],
    [680, 693, "NE"],
    [700, 714, "LA"],
    [716, 729, "AR"],
    [730, 732, "OK"],
    [733, 733, "TX"],
    [734, 749, "OK"],
    [750, 799, "TX"],
    [800, 816, "CO"],
    [820, 831, "WY"],
    [832, 838, "ID"],
    [840, 847, "UT"],
    [850, 865, "AZ"],
    [870, 884, "NM"],
    [885, 885, "TX"],
    [889, 898, "NV"],
    [900, 961, "CA"],
    [967, 968, "HI"],
    [969, 969, "GU"],
    [970, 979, "OR"],
    [980, 994, "WA"],
    [995, 999, "AK"],
]

const ZIP_PATTERN = /^\d{5}(?:-\d{4})?$/

export function isValidZip(zipcode: string): boolean {
    return ZIP_PATTERN.test(zipcode.trim())
}

/**
 * Resolve a US ZIP code to its state. Returns null for malformed, military, or unknown ZIPs.
 */
export function stateFromZip(zipcode: string): UsState | null {
    const trimmed = zipcode.trim()
    if (!ZIP_PATTERN.test(trimmed)) return null

    const prefix = Number(trimmed.slice(0, 3))
    if (Number.isNaN(prefix)) return null

    if (
        (prefix >= 90 && prefix <= 99) ||
        prefix === 340 ||
        (prefix >= 962 && prefix <= 966)
    ) {
        // Armed Forces mail uses AA/AE/AP rather than a state.
        return null
    }

    for (const [min, max, code] of ZIP_RANGES) {
        if (prefix >= min && prefix <= max) {
            return STATE_BY_CODE.get(code) ?? null
        }
    }
    return null
}
