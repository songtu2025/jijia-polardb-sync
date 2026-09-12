import { useState, type ReactNode } from "react";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";

import { createAntdTheme } from "../theme/antdTheme";

export function UiProvider({ children }: { children: ReactNode }) {
  const [theme] = useState(createAntdTheme);

  return (
    <ConfigProvider button={{ autoInsertSpace: false }} locale={zhCN} theme={theme}>
      {children}
    </ConfigProvider>
  );
}
