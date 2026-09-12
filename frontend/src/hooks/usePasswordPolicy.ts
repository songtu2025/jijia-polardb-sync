import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import { getApiErrorMessage } from "../pages/m3Utils";

export function usePasswordPolicy() {
  const [minimumLength, setMinimumLength] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => setAttempt((current) => current + 1), []);

  useEffect(() => {
    let active = true;
    setMinimumLength(null);
    setLoading(true);
    setError("");
    void api
      .getPasswordPolicy()
      .then((policy) => {
        if (active) setMinimumLength(policy.minimumLength);
      })
      .catch((caught: unknown) => {
        if (active) setError(getApiErrorMessage(caught, "密码规则加载失败，请稍后重试"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  return { error, loading, minimumLength, retry };
}
