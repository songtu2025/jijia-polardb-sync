import { render, screen } from "@testing-library/react";
import { Modal } from "antd";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { createAntdTheme } from "../theme/antdTheme";
import { UiProvider } from "./UiProvider";

const THEME_TOKENS = {
  "--primitive-primary": "#0c6b59",
  "--color-primary": "var(--primitive-primary)",
  "--color-surface-container": "#ffffff",
  "--color-surface-page": "#f7f9f9",
  "--color-border-control": "#7f8b85",
  "--color-border-soft": "#e8eeea",
  "--color-danger": "#b23333",
  "--color-info": "#3266a8",
  "--color-success": "#0c9b72",
  "--color-text-primary": "#141b18",
  "--color-text-disabled": "#7f8b85",
  "--color-text-placeholder": "#63736e",
  "--color-text-secondary": "#63736e",
  "--color-warning": "#b36618",
  "--radius-control": "7px",
  "--radius-overlay": "13px",
  "--control-height-default": "38px",
  "--control-height-large": "40px",
  "--control-height-small": "34px",
  "--font-family-sans": '"Microsoft YaHei", sans-serif',
  "--font-size-body": "14px",
  "--shadow-large": "0 20px 70px rgb(19 34 29 / 18%)",
};

describe("Ant Design 主题适配", () => {
  let previousStyle: string | null;

  beforeEach(() => {
    previousStyle = document.documentElement.getAttribute("style");
    Object.entries(THEME_TOKENS).forEach(([name, value]) => {
      document.documentElement.style.setProperty(name, value);
    });
  });

  afterEach(() => {
    if (previousStyle === null) {
      document.documentElement.removeAttribute("style");
    } else {
      document.documentElement.setAttribute("style", previousStyle);
    }
  });

  it("解析 SEEKWAY CSS 别名并映射关键主题令牌", () => {
    const theme = createAntdTheme();

    expect(theme.cssVar).toEqual({ prefix: "seekway" });
    expect(theme.token).toMatchObject({
      borderRadius: 7,
      colorPrimary: "#0c6b59",
      colorText: "#141b18",
      controlHeight: 38,
      fontSize: 14,
    });
  });

  it("提供中文 Ant Design 上下文", () => {
    render(
      <UiProvider>
        <Modal footer={null} open title="测试弹窗">
          弹窗内容
        </Modal>
      </UiProvider>,
    );

    expect(screen.getByRole("dialog", { name: "测试弹窗" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "关闭" })).toBeInTheDocument();
  });
});
