import { Form, Input } from "antd";

export interface NewPasswordValues {
  newPassword: string;
  confirmPassword: string;
}

export function PasswordFields({ minimumLength }: { minimumLength: number | null }) {
  const minimumLengthRule =
    minimumLength === null
      ? []
      : [{ min: minimumLength, message: `密码至少需要 ${minimumLength} 位` }];

  return (
    <>
      <Form.Item
        label="新密码"
        name="newPassword"
        rules={[{ required: true, message: "请输入新密码" }, ...minimumLengthRule]}
      >
        <Input.Password
          autoComplete="new-password"
          minLength={minimumLength ?? undefined}
          placeholder={minimumLength === null ? "等待密码要求" : `至少 ${minimumLength} 位`}
        />
      </Form.Item>
      <Form.Item
        dependencies={["newPassword"]}
        label="确认新密码"
        name="confirmPassword"
        rules={[
          { required: true, message: "请再次输入新密码" },
          ({ getFieldValue }) => ({
            validator(_, value: string) {
              return !value || getFieldValue("newPassword") === value
                ? Promise.resolve()
                : Promise.reject(new Error("两次输入的密码不一致"));
            },
          }),
        ]}
      >
        <Input.Password
          autoComplete="new-password"
          minLength={minimumLength ?? undefined}
          placeholder="再次输入新密码"
        />
      </Form.Item>
      <p className="password-hint">
        {minimumLength === null
          ? "密码要求加载后即可填写。"
          : `密码至少 ${minimumLength} 位；请勿使用与其他系统相同的密码。`}
      </p>
    </>
  );
}
