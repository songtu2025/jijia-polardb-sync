import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="brand-lockup brand-lockup--dark">
          <span className="brand-mark">积</span>
          <span>积加数据接入平台</span>
        </div>
        <nav aria-label="主导航">
          <span>接口</span>
          <span>运行</span>
          <span>数据</span>
          <span className="active">设置</span>
        </nav>
        <div className="top-nav-spacer" />
        <span className="top-nav-help">帮助</span>
        <span className="avatar" aria-label={user?.displayName ?? user?.email}>
          {(user?.displayName ?? user?.email ?? "管").slice(0, 1)}
        </span>
        <button className="text-button" type="button" onClick={handleLogout}>
          退出
        </button>
      </header>
      {children}
    </div>
  );
}
