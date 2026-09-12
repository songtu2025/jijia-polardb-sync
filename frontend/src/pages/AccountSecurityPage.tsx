import { useState } from "react";
import { Alert, Button, Form, Input } from "antd";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { PasswordFields, type NewPasswordValues } from "../components/PasswordFields";
import { usePasswordPolicy } from "../hooks/usePasswordPolicy";
import { getApiErrorMessage } from "./m3Utils";

interface ChangePasswordValues extends NewPasswordValues {
  currentPassword: string;
}

export function AccountSecurityPage() {
  const { csrfToken, user } = useAuth();
  const navigate = useNavigate();
  const [form] = Form.useForm<ChangePasswordValues>();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const policy = usePasswordPolicy();
  const formReady = policy.minimumLength !== null && !policy.loading && !policy.error;

  async function submit(values: ChangePasswordValues) {
    if (!csrfToken || policy.minimumLength === null) return;
    setSubmitting(true);
    setError("");
    try {
      await api.changePassword(values.currentPassword, values.newPassword, csrfToken);
      navigate("/login", { replace: true, state: { passwordChanged: true } });
    } catch (caught) {
      setError(getApiErrorMessage(caught, "密码修改失败，请稍后重试"));
      setSubmitting(false);
    }
  }

  return (
    <AppShell>
      <main className="m3-page account-security-page">
        <section className="m3-card account-security-card" aria-labelledby="security-heading">
          <header className="account-security-heading">
            <h1 id="security-heading">账号安全</h1>
          </header>
          {policy.loading ? (
            <Alert
              className="account-security-policy-status"
              title="正在读取密码要求…"
              type="info"
              showIcon
            />
          ) : null}
          {policy.error ? (
            <Alert
              action={<Button onClick={policy.retry}>重新加载</Button>}
              className="account-security-policy-status"
              description="暂时无法读取密码要求。表单已停用，请重新加载后再修改。"
              role="alert"
              title="密码服务暂不可用"
              type="error"
              showIcon
            />
          ) : null}
          <Form<ChangePasswordValues>
            form={form}
            layout="vertical"
            disabled={!formReady || submitting}
            requiredMark={false}
            validateTrigger="onBlur"
            scrollToFirstError={{ focus: true }}
            onFinish={(values) => void submit(values)}
          >
            <div className="account-security-field-heading">
              <label htmlFor="currentPassword">当前密码</label>
              <Link state={{ email: user?.email }} to="/forgot-password">
                忘记当前密码？
              </Link>
            </div>
            <Form.Item
              name="currentPassword"
              rules={[{ required: true, message: "请输入当前密码" }]}
            >
              <Input.Password
                autoComplete="current-password"
                id="currentPassword"
                placeholder="请输入当前密码"
              />
            </Form.Item>
            <PasswordFields minimumLength={policy.minimumLength} />
            {error ? (
              <Alert className="page-alert" role="alert" title={error} type="error" />
            ) : null}
            <div className="account-security-actions">
              <Button disabled={!formReady} htmlType="submit" loading={submitting} type="primary">
                {submitting ? "保存中…" : "修改密码"}
              </Button>
            </div>
          </Form>
        </section>
      </main>
    </AppShell>
  );
}
