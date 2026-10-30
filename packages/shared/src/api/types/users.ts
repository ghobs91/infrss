export enum UserRole {
  BASIC = 'BASIC',
  PRO = 'PRO',
  ADMIN = 'ADMIN',
}

export interface ProfileResponse {
  id: string;
  email: string;
  role: UserRole;
  is_onboarded: boolean;
  /** Optional US ZIP used to curate federal, state, and local government feeds. */
  government_zipcode: string | null;
  created_at: string;
  updated_at: string;
}

// Alias for backward compatibility if needed, though ProfileResponse is preferred
export type User = ProfileResponse;
export type UserProfile = ProfileResponse;

export interface ProfileUpdate {
  email?: string;
  is_onboarded?: boolean;
  /** US ZIP code for the government catalog; null clears the saved location. */
  government_zipcode?: string | null;
}

export interface TokenData {
  sub: string;
  email?: string;
  role?: string;
}
