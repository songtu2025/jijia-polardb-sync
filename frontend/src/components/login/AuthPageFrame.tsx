import type { ReactNode } from "react";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";

import { loginTheme } from "../../theme/antdTheme";
import { BrandArtwork } from "./BrandArtwork";
import logo from "./assets/seekway-mark-inverse.svg";
import "./seekway-login.css";

export function AuthPageFrame({
  children,
  subtitle,
  title,
}: {
  children: ReactNode;
  subtitle?: string;
  title: string;
}) {
  return (
    <ConfigProvider
      theme={loginTheme}
      locale={{ ...zhCN, global: { ...zhCN.global, show: "显示密码", hide: "隐藏密码" } }}
    >
      <main className="seekway-login">
        <section className="seekway-login__brand" aria-label="SEEKWAY 品牌">
          <div className="seekway-login__signature">
            <div className="seekway-login__logo" role="img" aria-label="SEEKWAY">
              <img src={logo} alt="" width="48" height="48" />
              <span>SEEKWAY</span>
            </div>
            <p className="seekway-login__brand-meaning">风起为帆，行而成路。</p>
          </div>
          <div className="seekway-login__art">
            <BrandArtwork />
          </div>
        </section>
        <section className="seekway-login__entry" aria-labelledby="auth-page-title">
          <div className="seekway-login__form">
            <header className="seekway-login__heading">
              <h1 id="auth-page-title">{title}</h1>
              {subtitle ? <p>{subtitle}</p> : null}
            </header>
            {children}
          </div>
        </section>
      </main>
    </ConfigProvider>
  );
}
