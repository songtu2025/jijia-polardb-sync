import { useEffect, useState } from "react";
import { Alert, Button, Form, Spin } from "antd";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { AuthPageFrame } from "../components/login/AuthPageFrame";
import { PasswordFields, type NewPasswordValues } from "../components/PasswordFields";
import { usePasswordPolicy } from "../hooks/usePasswordPolicy";
import { getApiErrorMessage } from "./m3Utils";

export function ResetPasswordPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [form] = Form.useForm<NewPasswordValues>();
  const [token] = useState(
    () =>
      new URLSearchParams(location.hash.startsWith("#") ? location.hash.slice(1) : "").get(
        "token",
      ) ?? "",
  );
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [tokenError, setTokenError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const policy = usePasswordPolicy();

  useEffect(() => {
    let active = true;
    if (!token) {
      setTokenError("重置链接缺少令牌，请重新申请");
      setValidating(false);
      return () => {
        active = false;
      };
    }
    void api
      .validatePasswordReset(token)
      .then((result) => {
        if (active) setTokenValid(result.valid);
      })
      .catch((caught: unknown) => {
        if (active) setTokenError(getApiErrorMessage(caught, "重置链接无效或已过期"));
      })
      .finally(() => {
        if (active) setValidating(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function submit(values: NewPasswordValues) {
    if (!tokenValid || policy.minimumLength === null) return;
    setSubmitting(true);
    setError("");
    try {
      await api.completePasswordReset(token, values.newPassword);
      navigate("/login", { replace: true, state: { passwordReset: true } });
    } catch (caught) {
      setError(getApiErrorMessage(caught, "密码重置失败，请重新申请重置链接"));
      setSubmitting(false);
    }
  }

  return (
    <AuthPageFrame title="设置新密码" subtitle="重置链接只能使用一次">
      {validating || policy.loading ? (
        <div className="empty-state">
          <Spin /> 正在验证重置链接…
        </div>
      ) : null}
      {tokenError || policy.error ? (
        <Alert
          role="alert"
          title={tokenError || policy.error}
          description={<Link to="/forgot-password">重新申请重置链接</Link>}
          type="error"
          showIcon
        />
      ) : null}
      {tokenValid && policy.minimumLength !== null ? (
        <Form<NewPasswordValues>
          form={form}
          layout="vertical"
          disabled={submitting}
          requiredMark={false}
          validateTrigger="onBlur"
          scrollToFirstError={{ focus: true }}
          onFinish={(values) => void submit(values)}
        >
          <PasswordFields minimumLength={policy.minimumLength} />
          <Button block htmlType="submit" loading={submitting} type="primary">
            {submitting ? "保存中…" : "重置密码"}
          </Button>
          {error ? (
            <Alert className="seekway-login__feedback" role="alert" title={error} type="error" />
          ) : null}
        </Form>
      ) : null}
      <p className="seekway-login__help">
        <Link to="/login">返回登录</Link>
      </p>
    </AuthPageFrame>
  );
}
