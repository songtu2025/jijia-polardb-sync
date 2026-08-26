import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { MembersPage } from "./pages/MembersPage";
import { RegisterPage } from "./pages/RegisterPage";

function ProtectedRoute({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { ready, user } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="app-loading">正在恢复登录状态…</div>;
  if (!user) return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  if (admin && user.role !== "admin") return <Navigate replace to="/" />;
  return children;
}

function StartPage() {
  const { user } = useAuth();
  if (user?.role === "admin") return <Navigate replace to="/members" />;
  return <HomePage />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/members"
        element={<ProtectedRoute admin><MembersPage /></ProtectedRoute>}
      />
      <Route path="/" element={<ProtectedRoute><StartPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate replace to="/" />} />
    </Routes>
  );
}
