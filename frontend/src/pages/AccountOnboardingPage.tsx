import { useState } from "react";
import { Alert, Button, Form, Input, Progress, Tag } from "antd";
import { Link, useNavigate } from "react-router-dom";

import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";

const onboardingSteps = [
  { title: "填写凭证", detail: "安全保存 App 凭证" },
  { title: "验证连接", detail: "仅验证访问凭证" },
  { title: "配置接口", detail: "启用同步范围与计划" },
  { title: "首次同步", detail: "预览范围后开始任务" },
];

export function AccountOnboardingPage() {
  const { csrfToken } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [appId, setAppId] = useState("");
  const [appKey, setAppKey] = useState("");
  const [showAppKey, setShowAppKey] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState<1 | 2>(1);

  const requiredFields = [
    { label: "账号名称", complete: Boolean(name.trim()) },
    { label: "appId", complete: Boolean(appId.trim()) },
    { label: "appKey", complete: Boolean(appKey.trim()) },
  ];
  const completedFieldCount = requiredFields.filter((field) => field.complete).length;
  const isReady = completedFieldCount === requiredFields.length;
  const currentStepName = step === 1 ? "填写凭证" : "验证连接";

  async function handleSubmit() {
    if (!csrfToken) return;
    setBusy(true);
    setError("");
    try {
      const account = await api.createAccount(name, appId, appKey, csrfToken);
      setStep(2);
      try {
        await api.verifyAccount(account.id, csrfToken);
      } catch (caught) {
        const message = caught instanceof ApiError ? caught.message : "验证失败，请稍后重试";
        navigate(`/accounts/${account.id}`, {
          replace: true,
          state: {
            accountError: `账号“${account.name}”已创建，但验证失败：${message}。请检查凭证后重新验证。`,
          },
        });
        return;
      }
      navigate(`/accounts/${account.id}/policies`, {
        replace: true,
        state: {
          policyNotice: `账号“${account.name}”已验证通过。请启用需要同步的接口，再发起首次同步。`,
        },
      });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "账号接入失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <main className="account-onboarding" data-node-id="38:333">
        <header className="onboarding-heading">
          <Link aria-label="返回账号列表" className="onboarding-back-link" to="/accounts">
            <span aria-hidden="true">←</span>
            账号列表
          </Link>
          <div className="onboarding-title">
            <nav aria-label="面包屑" className="onboarding-breadcrumb">
              <Link to="/accounts">接入管理</Link>
              <span aria-hidden="true">/</span>
              <span aria-current="page">账号接入</span>
            </nav>
            <h1>接入积加 API 用户</h1>
          </div>
          <div className="onboarding-step-status">
            <small>当前进度</small>
            <strong>
              第 {step} 步 · {currentStepName}
            </strong>
          </div>
        </header>

        <ol aria-label="账号接入步骤" className="account-stepper">
          {onboardingSteps.map((item, index) => {
            const stepNumber = index + 1;
            const isComplete = stepNumber < step;
            const isCurrent = stepNumber === step;
            const state = isComplete ? "done" : isCurrent ? "active" : "pending";
            return (
              <li aria-current={isCurrent ? "step" : undefined} className={state} key={item.title}>
                <i aria-hidden="true">{isComplete ? "✓" : stepNumber}</i>
                <span>
                  <strong>{item.title}</strong>
                  <small>{item.detail}</small>
                </span>
              </li>
            );
          })}
        </ol>

        <section className="onboarding-workspace">
          <Form className="account-connect-form" layout="vertical" onFinish={handleSubmit}>
            <fieldset>
              <legend>
                <b>01</b> 基本信息
              </legend>
              <Form.Item htmlFor="account-name" label="账号名称" required>
                <Input
                  id="account-name"
                  placeholder="例如：北美业务账号"
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Form.Item>
            </fieldset>

            <fieldset>
              <legend>
                <b>02</b> 凭证录入
              </legend>
              <p>凭证将加密保存；appKey 提交后无法在页面回显。</p>
              <div className="credential-fields">
                <Form.Item htmlFor="account-app-id" label="appId" required>
                  <Input
                    autoComplete="off"
                    id="account-app-id"
                    required
                    spellCheck={false}
                    value={appId}
                    onChange={(event) => setAppId(event.target.value)}
                  />
                </Form.Item>
                <Form.Item htmlFor="account-app-key" label="appKey" required>
                  <div className="secret-input">
                    <Input
                      autoComplete="new-password"
                      id="account-app-key"
                      required
                      spellCheck={false}
                      type={showAppKey ? "text" : "password"}
                      value={appKey}
                      onChange={(event) => setAppKey(event.target.value)}
                    />
                    <Button
                      aria-controls="account-app-key"
                      aria-label={showAppKey ? "隐藏 appKey" : "显示 appKey"}
                      aria-pressed={showAppKey}
                      onClick={() => setShowAppKey((current) => !current)}
                    >
                      {showAppKey ? "隐藏" : "显示"}
                    </Button>
                  </div>
                </Form.Item>
              </div>
            </fieldset>

            {error ? <Alert className="page-alert" showIcon title={error} type="error" /> : null}
            <div className="account-security-note">
              <strong>验证失败时账号仍会保留</strong>
              <span>可在账号详情中更新凭证并重新验证；界面不会回显 appKey 或临时访问凭证。</span>
            </div>
            <footer>
              <Link className="action-link action-link--neutral" to="/accounts">
                取消
              </Link>
              <Button disabled={!isReady} htmlType="submit" loading={busy} type="primary">
                创建并验证账号
              </Button>
            </footer>
          </Form>

          <aside aria-labelledby="onboarding-checker-title" className="onboarding-inspector">
            <div className="onboarding-inspector-heading">
              <Tag
                aria-live="polite"
                className={`onboarding-status ${isReady ? "onboarding-status--ready" : "onboarding-status--pending"}`}
                role="status"
              >
                {isReady ? "可以创建" : `待填写 ${requiredFields.length - completedFieldCount} 项`}
              </Tag>
              <h2 id="onboarding-checker-title">接入检查器</h2>
            </div>

            <div className="onboarding-completion">
              <div>
                <span>必填项完成度</span>
                <strong>
                  {completedFieldCount} / {requiredFields.length}
                </strong>
              </div>
              <Progress
                aria-label="必填项完成度"
                aria-valuetext={`${completedFieldCount} / ${requiredFields.length}`}
                percent={(completedFieldCount / requiredFields.length) * 100}
                showInfo={false}
              />
            </div>

            <ul aria-label="必填项状态" className="onboarding-checklist">
              {requiredFields.map((field, index) => (
                <li className={field.complete ? "done" : ""} key={field.label}>
                  <i aria-hidden="true">{field.complete ? "✓" : index + 1}</i>
                  <span>
                    <strong>{field.label}</strong>
                    <small>{field.complete ? "已填写" : "等待填写"}</small>
                  </span>
                </li>
              ))}
            </ul>

            <details className="onboarding-result-summary">
              <summary>提交后会发生什么</summary>
              <dl>
                <dt>凭证</dt>
                <dd>加密保存</dd>
                <dt>连接验证</dt>
                <dd>只获取临时访问凭证</dd>
                <dt>接口策略</dt>
                <dd>全部默认关闭</dd>
              </dl>
            </details>
          </aside>
        </section>
      </main>
    </AppShell>
  );
}
