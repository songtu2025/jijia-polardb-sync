import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { BrandPanel } from "../components/BrandPanel";
import { FormField } from "../components/FormField";

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return <Navigate replace to={user.role === "admin" ? "/members" : "/"} />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const signedInUser = await login(email, password);
      const requested = (location.state as { from?: string } | null)?.from;
      navigate(
        requested ?? (signedInUser.role === "admin" ? "/members" : "/"),
        { replace: true },
      );
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "登录失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout" data-node-id="120:432">
      <BrandPanel mode="login" />
      <section className="auth-main">
        <div className="auth-top-note">仅限受邀成员使用</div>
        <form className="auth-form auth-form--login" onSubmit={handleSubmit}>
          <h2>欢迎回来</h2>
          <p className="auth-description">使用管理员为你开通的邮箱和密码登录。</p>
          <div className="auth-fields">
            <FormField
              autoComplete="email"
              id="email"
              label="邮箱"
              placeholder="name@example.com"
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <FormField
              autoComplete="current-password"
              id="password"
              label="密码"
              placeholder="请输入密码"
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          {error ? <div className="form-alert" role="alert">{error}</div> : null}
          <button className="primary-button auth-submit" disabled={submitting} type="submit">
            {submitting ? "登录中…" : "登录"}
          </button>
          <p className="form-help">无法登录？请联系管理员确认账号状态。</p>
        </form>
      </section>
    </main>
  );
}
