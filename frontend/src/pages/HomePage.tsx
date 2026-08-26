import { AppShell } from "../components/AppShell";
import { useAuth } from "../auth/AuthContext";

const roleNames = {
  admin: "管理员",
  operator: "操作员",
  viewer: "只读成员",
};

export function HomePage() {
  const { user } = useAuth();
  return (
    <AppShell>
      <main className="signed-in-home">
        <span className="status-dot" />
        <h1>登录成功</h1>
        <p>
          {user?.displayName ?? user?.email} · {user ? roleNames[user.role] : ""}
        </p>
        <small>本阶段仅开放身份认证与成员权限功能。</small>
      </main>
    </AppShell>
  );
}
