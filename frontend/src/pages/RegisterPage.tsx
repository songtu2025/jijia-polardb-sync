import { useEffect, useState } from "react";
import { Alert, Button, Form, Input, Spin } from "antd";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { api, ApiError } from "../api/client";
import type { InvitationValidation, UserRole } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { BrandPanel } from "../components/BrandPanel";
import { PasswordFields, type NewPasswordValues } from "../components/PasswordFields";
import { usePasswordPolicy } from "../hooks/usePasswordPolicy";

interface RegisterValues extends NewPasswordValues {
  displayName: string;
}

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
  const [form] = Form.useForm<RegisterValues>();
  const policy = usePasswordPolicy();
  const [invitation, setInvitation] = useState<InvitationValidation | null>(null);
  const [loading, setLoading] = useState(true);
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
    return <Navigate replace to="/" />;
  }

  async function handleSubmit(values: RegisterValues) {
    setError("");
    setSubmitting(true);
    try {
      await register(token, values.displayName, values.newPassword);
      navigate("/", { replace: true });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "注册失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout" data-node-id="120:433">
      <BrandPanel />
      <section className="auth-main">
        <div className="auth-top-note auth-top-note--link">
          已有账号？<Link to="/login">返回登录</Link>
        </div>
        <Form<RegisterValues>
          className="auth-form"
          disabled={submitting}
          form={form}
          layout="vertical"
          requiredMark={false}
          validateTrigger="onBlur"
          scrollToFirstError={{ focus: true }}
          onFinish={(values) => void handleSubmit(values)}
        >
          <h1>完成账号注册</h1>
          {loading || policy.loading ? (
            <div className="invitation-card">
              <Spin size="small" /> 正在加载注册信息…
            </div>
          ) : null}
          {invitation ? (
            <div className="invitation-card">
              <strong>受邀邮箱</strong>
              <span>{invitation.email}</span>
              <strong>固定角色</strong>
              <span>{roleNames[invitation.role]}</span>
            </div>
          ) : null}
          {policy.error ? (
            <Alert
              action={<Button onClick={policy.retry}>重试</Button>}
              title={policy.error}
              type="error"
              showIcon
            />
          ) : null}
          {!loading && invitation && policy.minimumLength !== null ? (
            <>
              <div className="auth-fields auth-fields--register">
                <Form.Item
                  label="姓名"
                  name="displayName"
                  rules={[{ required: true, whitespace: true, message: "请输入姓名" }]}
                >
                  <Input autoComplete="name" placeholder="请输入你的姓名" />
                </Form.Item>
                <PasswordFields minimumLength={policy.minimumLength} />
              </div>
            </>
          ) : null}
          {error ? <Alert title={error} type="error" /> : null}
          {invitation && policy.minimumLength !== null ? (
            <Button
              autoInsertSpace={false}
              block
              className="auth-submit"
              disabled={submitting}
              htmlType="submit"
              loading={submitting}
              type="primary"
            >
              {submitting ? "注册中…" : "完成注册"}
            </Button>
          ) : null}
        </Form>
      </section>
    </main>
  );
}
