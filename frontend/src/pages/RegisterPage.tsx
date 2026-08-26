import { type FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { InvitationValidation, UserRole } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { BrandPanel } from "../components/BrandPanel";
import { FormField } from "../components/FormField";

const roleNames: Record<UserRole, string> = {
  admin: "管理员",
  operator: "操作员",
  viewer: "只读成员",
};

export function RegisterPage() {
  const { hash } = useLocation();
  const token = new URLSearchParams(hash.slice(1)).get("token") ?? "";
  const { register, user } = useAuth();
  const navigate = useNavigate();
  const [invitation, setInvitation] = useState<InvitationValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("邀请链接缺少令牌，请联系管理员重新发送");
      setLoading(false);
      return;
    }
    api
      .validateInvitation(token)
      .then(setInvitation)
      .catch((caught: unknown) => {
        setError(caught instanceof ApiError ? caught.message : "邀请验证失败");
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (user) {
    return <Navigate replace to={user.role === "admin" ? "/members" : "/"} />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    if (password.length < 12) {
      setError("密码至少需要 12 位");
      return;
    }
    setSubmitting(true);
    try {
      const registeredUser = await register(token, displayName, password);
      navigate(registeredUser.role === "admin" ? "/members" : "/", {
        replace: true,
      });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "注册失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout" data-node-id="120:433">
      <BrandPanel mode="register" />
      <section className="auth-main auth-main--register">
        <div className="auth-top-note auth-top-note--link">
          已有账号？<Link to="/login">返回登录</Link>
        </div>
        <form className="auth-form auth-form--register" onSubmit={handleSubmit}>
          <h2>完成账号注册</h2>
          <p className="auth-description">确认邀请信息，并设置用于后续登录的密码。</p>
          {loading ? <div className="invitation-card">正在验证邀请…</div> : null}
          {invitation ? (
            <div className="invitation-card">
              <strong>受邀邮箱</strong><span>{invitation.email}</span>
              <strong>固定角色</strong><span>{roleNames[invitation.role]}</span>
            </div>
          ) : null}
          {!loading && invitation ? (
            <>
              <div className="auth-fields auth-fields--register">
                <FormField
                  autoComplete="name"
                  id="display-name"
                  label="姓名"
                  placeholder="请输入你的姓名"
                  required
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
                <FormField
                  autoComplete="new-password"
                  id="new-password"
                  label="密码"
                  minLength={12}
                  placeholder="至少 12 位"
                  required
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <FormField
                  autoComplete="new-password"
                  id="confirm-password"
                  label="确认密码"
                  minLength={12}
                  placeholder="再次输入密码"
                  required
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </div>
              <p className="password-hint">密码至少 12 位；请勿使用与其他系统相同的密码。</p>
            </>
          ) : null}
          {error ? <div className="form-alert" role="alert">{error}</div> : null}
          {invitation ? (
            <button className="primary-button auth-submit" disabled={submitting} type="submit">
              {submitting ? "注册中…" : "完成注册"}
            </button>
          ) : null}
        </form>
      </section>
    </main>
  );
}
