interface BrandPanelProps {
  mode: "login" | "register";
}

const content = {
  login: {
    title: (
      <>
        让数据接入
        <br />
        稳定、透明、可追踪
      </>
    ),
    description: "统一管理接口、运行任务与原始数据，让每一次同步都有据可查。",
    features: [
      "服务端会话，敏感凭据不进入浏览器存储",
      "固定角色权限，关键操作全程受控",
      "仅限受邀成员加入",
    ],
    noteTitle: "受邀访问",
    note: "如果你还没有账号，请联系管理员发送邀请邮件。",
  },
  register: {
    title: (
      <>
        一封邀请，
        <br />
        开启可靠的数据协作
      </>
    ),
    description: "完成账号设置后，你将按受邀角色访问平台，权限边界清晰可见。",
    features: [
      "邀请邮箱不可更改",
      "角色由管理员预先指定",
      "邀请链接仅可使用一次",
    ],
    noteTitle: "邀请确认",
    note: "请确认邮箱与角色信息无误，再设置你的登录密码。",
  },
};

export function BrandPanel({ mode }: BrandPanelProps) {
  const item = content[mode];
  return (
    <aside className="brand-panel">
      <div className="brand-lockup">
        <span className="brand-mark brand-mark--light">积</span>
        <span>积加数据接入平台</span>
      </div>
      <div className="brand-message">
        <h1>{item.title}</h1>
        <p>{item.description}</p>
        <ul>
          {item.features.map((feature) => (
            <li key={feature}>✓&nbsp;&nbsp;{feature}</li>
          ))}
        </ul>
      </div>
      <div className="brand-note">
        <strong>{item.noteTitle}</strong>
        <span>{item.note}</span>
      </div>
    </aside>
  );
}
