import { ApiClient } from '../core';
import type { UserProfile, ProfileUpdate } from '../types/users';

export const users = {
  getProfile: () => ApiClient.get<UserProfile>('/api/users/profile'),
  updateProfile: (data: ProfileUpdate) => ApiClient.patch<UserProfile>('/api/users/profile', data),
  deleteAccount: () => ApiClient.delete<void>('/api/users/account'),
};
