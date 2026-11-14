import { ApiClient } from '../core';
import { FeedDiscoveryReport, FeedDiscoveryResult } from '../types';

export const discover = {
  /**
   * Preview a URL that is already known to be a feed.
   */
  previewFeed: (url: string) => {
    const queryParams = new URLSearchParams();
    queryParams.append('url', url);
    return ApiClient.get<FeedDiscoveryResult>(`/api/discover/preview?${queryParams.toString()}`);
  },

  /**
   * Find the feeds a website publishes, for a URL pasted into Discover.
   *
   * Tries the URL as a feed first, then runs the backend discovery ladder until a verified feed
   * turns up. Every attempted strategy is reported alongside the feeds that were found.
   */
  findFeeds: (url: string) => {
    const queryParams = new URLSearchParams();
    queryParams.append('url', url);
    return ApiClient.get<FeedDiscoveryReport>(`/api/discover/find?${queryParams.toString()}`);
  },
};
