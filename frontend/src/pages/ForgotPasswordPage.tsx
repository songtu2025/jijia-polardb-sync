import { useState } from "react";
import { Alert, Button, Form, Input } from "antd";
import { Link, useLocation } from "react-router-dom";

import { api } from "../api/client";
import { AuthPageFrame } from "../components/login/AuthPageFrame";
import { getApiErrorMessage } from "./m3Utils";

interface ForgotPasswordValues {
  email: string;
}

export function ForgotPasswordPage() {
  const location = useLocation();
  const routeState = location.state as { email?: unknown } | null;
  const initialEmail = typeof routeState?.email === "string" ? routeState.email : "";
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");

  async function submit(values: ForgotPasswordValues) {
    setSubmitting(true);
    setError("");
    try {
      await api.requestPasswordReset(values.email);
      setAccepted(true);
    } catch (caught) {
      setError(getApiErrorMessage(caught, "暂时无法发送重置邮件，请稍后重试"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPageFrame title="重置登录密码" subtitle="输入账号邮箱，我们会发送一次性重置链接">
      {accepted ? (
        <>
          <Alert
            role="status"
            title="如果该邮箱已注册，重置邮件将很快送达。"
            description="请检查收件箱和垃圾邮件。为保护账号信息，我们不会显示邮箱是否存在。"
            type="success"
            showIcon
          />
          <p className="seekway-login__help">
            <Link to="/login">返回登录</Link>
          </p>
        </>
      ) : (
        <Form<ForgotPasswordValues>
          initialValues={{ email: initialEmail }}
          layout="vertical"
          disabled={submitting}
          requiredMark={false}
          validateTrigger="onBlur"
          scrollToFirstError={{ focus: true }}
          onFinish={(values) => void submit(values)}
        >
          <Form.Item
            label="邮箱"
            name="email"
            rules={[
              { required: true, whitespace: true, message: "请输入邮箱" },
              { type: "email", message: "请输入有效的邮箱地址" },
            ]}
          >
            <Input autoComplete="email" placeholder="name@example.com" type="email" />
          </Form.Item>
          <Button block htmlType="submit" loading={submitting} type="primary">
            {submitting ? "发送中…" : "发送重置邮件"}
          </Button>
          {error ? (
            <Alert className="seekway-login__feedback" role="alert" title={error} type="error" />
          ) : null}
          <p className="seekway-login__help">
            想起密码了？<Link to="/login">返回登录</Link>
          </p>
        </Form>
      )}
    </AuthPageFrame>
  );
}
