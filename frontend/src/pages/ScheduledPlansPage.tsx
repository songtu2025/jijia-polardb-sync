import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { ScheduledPlansPanel } from "../components/ScheduledPlansPanel";

export function ScheduledPlansPage() {
  const { user } = useAuth();
  const location = useLocation();
  const canManage = user?.role === "admin" || user?.role === "operator";
  const returnTo = `${location.pathname}${location.search}`;
  const account = new URLSearchParams(location.search).get("account");
  const createParams = new URLSearchParams();
  if (account) createParams.set("accountId", account);
  return (
    <AppShell>
      <main className="m3-page">
        <header className="page-heading">
          <h1>定时计划</h1>
        </header>
        <ScheduledPlansPanel
          canManage={canManage}
          returnTo={returnTo}
          returnState={location.state}
          createAction={
            canManage ? (
              <Link
                className="action-link action-link--primary"
                to={`/jobs/plans/new${createParams.size ? `?${createParams}` : ""}`}
                state={{ from: returnTo, backLabel: "返回定时计划", returnState: location.state }}
              >
                创建定时计划
              </Link>
            ) : null
          }
        />
      </main>
    </AppShell>
  );
}
