import type { ThemeConfig } from "antd";

const CSS_REFERENCE_PATTERN = /^var\((--[\w-]+)\)$/;

/** V1.8.1 登录模板的局部尺寸和对比度，其余继承全局主题。 */
export const loginTheme: ThemeConfig = {
  token: { controlHeight: 58, fontSize: 18 },
  components: {
    Form: { itemMarginBottom: 40 },
    Input: { colorBorder: "#82928a", colorTextPlaceholder: "#66736d" },
  },
};

function readToken(styles: CSSStyleDeclaration, name: string): string {
  let value = styles.getPropertyValue(name).trim();
  const visited = new Set<string>();

  while (CSS_REFERENCE_PATTERN.test(value)) {
    const reference = value.match(CSS_REFERENCE_PATTERN)?.[1];
    if (!reference || visited.has(reference)) break;
    visited.add(reference);
    value = styles.getPropertyValue(reference).trim();
  }

  return value;
}

function readSize(styles: CSSStyleDeclaration, name: string): number {
  return Number.parseFloat(readToken(styles, name));
}

export function createAntdTheme(): ThemeConfig {
  const styles = getComputedStyle(document.documentElement);

  return {
    cssVar: { prefix: "seekway" },
    token: {
      colorBgBase: readToken(styles, "--color-surface-container"),
      colorBgContainerDisabled: readToken(styles, "--color-surface-disabled"),
      colorBgLayout: readToken(styles, "--color-surface-page"),
      colorBgTextActive: readToken(styles, "--color-primary-subtle"),
      colorBgTextHover: readToken(styles, "--color-surface-hover"),
      colorBorder: readToken(styles, "--color-border-control"),
      colorBorderSecondary: readToken(styles, "--color-border-soft"),
      colorError: readToken(styles, "--color-danger"),
      colorErrorBg: readToken(styles, "--color-danger-subtle"),
      colorErrorBorder: readToken(styles, "--color-danger-border"),
      colorErrorOutline: readToken(styles, "--color-danger"),
      colorInfo: readToken(styles, "--color-info"),
      colorInfoBg: readToken(styles, "--color-info-subtle"),
      colorInfoBorder: readToken(styles, "--color-info-border"),
      colorPrimary: readToken(styles, "--color-primary"),
      colorPrimaryActive: readToken(styles, "--color-primary-active"),
      colorPrimaryHover: readToken(styles, "--color-primary-hover"),
      colorSuccess: readToken(styles, "--color-success"),
      colorSuccessBg: readToken(styles, "--color-success-subtle"),
      colorSuccessBorder: readToken(styles, "--color-success-border"),
      colorText: readToken(styles, "--color-text-primary"),
      colorTextDisabled: readToken(styles, "--color-text-disabled"),
      colorTextPlaceholder: readToken(styles, "--color-text-placeholder"),
      colorTextSecondary: readToken(styles, "--color-text-secondary"),
      colorWarning: readToken(styles, "--color-warning"),
      colorWarningOutline: readToken(styles, "--color-warning-text"),
      borderRadius: readSize(styles, "--radius-control"),
      borderRadiusLG: readSize(styles, "--radius-overlay"),
      controlHeight: readSize(styles, "--control-height-default"),
      controlHeightLG: readSize(styles, "--control-height-large"),
      controlHeightSM: readSize(styles, "--control-height-small"),
      controlItemBgActive: readToken(styles, "--color-primary-subtle"),
      controlItemBgActiveDisabled: readToken(styles, "--color-surface-disabled"),
      controlItemBgActiveHover: readToken(styles, "--color-primary-subtle"),
      controlItemBgHover: readToken(styles, "--color-surface-hover"),
      controlOutline: readToken(styles, "--color-focus"),
      controlOutlineWidth: 2,
      fontFamily: readToken(styles, "--font-family-sans"),
      fontSize: readSize(styles, "--font-size-body"),
      lineWidthFocus: 2,
      motionDurationFast: readToken(styles, "--motion-duration-fast"),
      motionDurationMid: readToken(styles, "--motion-duration-default"),
      motionDurationSlow: readToken(styles, "--motion-duration-slow"),
      opacityLoading: 0.65,
      boxShadowSecondary: readToken(styles, "--shadow-large"),
    },
  };
}
