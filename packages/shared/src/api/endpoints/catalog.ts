import { ApiClient } from '../core';
import type { CatalogFeed, PrimaryEntity } from '../types/catalog';
import type { Subscription } from '../types/feeds';

export const catalog = {
  listCatalogEntities: (params?: { limit?: number; offset?: number }) => {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', String(params.limit));
    if (params?.offset) queryParams.append('offset', String(params.offset));
    const queryString = queryParams.toString();
    return ApiClient.get<PrimaryEntity[]>(
      `/api/catalog/entities${queryString ? `?${queryString}` : ''}`
    );
  },

  listCatalogFeeds: (params?: { entityId?: string; limit?: number; offset?: number }) => {
    const queryParams = new URLSearchParams();
    if (params?.entityId) queryParams.append('entity_id', params.entityId);
    if (params?.limit) queryParams.append('limit', String(params.limit));
    if (params?.offset) queryParams.append('offset', String(params.offset));
    const queryString = queryParams.toString();
    return ApiClient.get<CatalogFeed[]>(
      `/api/catalog/feeds${queryString ? `?${queryString}` : ''}`
    );
  },

  subscribeCatalogFeed: (feedId: string, folderId?: string) => {
    const queryParams = new URLSearchParams();
    if (folderId) queryParams.append('folder_id', folderId);
    const queryString = queryParams.toString();
    return ApiClient.post<Subscription>(
      `/api/catalog/feeds/${feedId}/subscribe${queryString ? `?${queryString}` : ''}`
    );
  },
};
