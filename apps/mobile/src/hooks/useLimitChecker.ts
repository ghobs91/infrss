import { isCodexUnlimited, useUserLimits } from '@infrss/shared';

/**
 * Reads the caller's plan limits and answers whether a given action is allowed.
 *
 * The paywall has been removed, so the server now reports unlimited limits for every user and
 * these checks always pass. The gate is kept as a defensive check for the (now impossible)
 * case of a metered limit coming back.
 */
export function useLimitChecker() {
  const { data: limitData, isLoading, refetch } = useUserLimits();

  const canAddFeed = () => {
    if (!limitData) return true;

    const { limits, usage } = limitData;
    // -1 signifies unlimited
    if (limits.max_subscriptions === -1) return true;
    return usage.subscriptions < limits.max_subscriptions;
  };

  const canUseAI = () => {
    if (!limitData) return true;

    const { limits, usage } = limitData;
    // -1 signifies unlimited
    if (limits.max_daily_ai_calls === -1) return true;
    return usage.daily_ai_calls < limits.max_daily_ai_calls;
  };

  const canUseCodex = () => {
    if (!limitData) return true;

    const usage = limitData.usage.codex;
    if (!usage) return true;
    if (isCodexUnlimited(usage)) return true;
    // Only reachable if a metered allowance ever returns: `used` is the completed count against
    // `limit`, and `used_in_window` (0 or 1) additionally gates the rolling-window allowance.
    return usage.used < usage.limit && (usage.used_in_window ?? 0) < 1;
  };

  const checkAccess = (type: 'feed' | 'ai' | 'codex') => {
    if (type === 'feed') return canAddFeed();
    if (type === 'ai') return canUseAI();
    if (type === 'codex') return canUseCodex();
    return true;
  };

  return {
    limitData,
    isLoading,
    canAddFeed,
    canUseAI,
    canUseCodex,
    checkAccess,
    refetch,
  };
}
