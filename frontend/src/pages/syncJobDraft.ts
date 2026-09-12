export interface SyncJobDraft {
  accountId: string;
  apiCode: string;
  rangeMode: "checkpoint" | "custom";
  startDate: string;
  endDate: string;
  marketScopeMode: "all" | "selected";
  selectedMarketIds: number[];
}

export function readSyncJobDraft(state: unknown, query: URLSearchParams): SyncJobDraft | undefined {
  const draft = (state as { syncJobDraft?: SyncJobDraft } | null)?.syncJobDraft;
  if (!draft) return undefined;
  if (query.has("accountId") && query.get("accountId") !== draft.accountId) return undefined;
  if (query.has("apiCode") && query.get("apiCode") !== draft.apiCode) return undefined;
  return draft;
}

export function buildPolicyRecovery(
  draft: SyncJobDraft,
  navigation: { path: string; label: string; state?: unknown },
) {
  const { accountId, apiCode } = draft;
  return {
    policyTarget: `/accounts/${accountId}/policies${apiCode ? `?apiCode=${encodeURIComponent(apiCode)}` : ""}`,
    policyNavigationState: {
      from: `/jobs/new?${new URLSearchParams({ accountId, ...(apiCode ? { apiCode } : {}) })}`,
      backLabel: "返回任务配置",
      returnState: {
        from: navigation.path,
        backLabel: navigation.label,
        returnState: navigation.state,
        syncJobDraft: draft,
      },
    },
  };
}
