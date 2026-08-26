import { type FormEvent, useEffect, useMemo, useState } from "react";

import { api, ApiError } from "../api/client";
import type { Invitation, User, UserRole, UserStatus } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { FormField } from "../components/FormField";
import { Modal } from "../components/Modal";

const roleNames: Record<UserRole, string> = {
  admin: "管理员",
  operator: "操作员",
  viewer: "只读成员",
};
const statusNames: Record<UserStatus, string> = {
  invited: "待接受",
  active: "已启用",
  disabled: "已停用",
};
const rolePolicies = [
  { role: "admin" as const, mark: "管", title: "全部敏感操作", detail: "凭证、发布、成员与审计" },
  { role: "operator" as const, mark: "操", title: "日常配置与运行", detail: "编辑草稿、运行与重试" },
  { role: "viewer" as const, mark: "只", title: "只查看与脱敏数据", detail: "不能修改、运行或导出" },
];
const permissions: Record<UserRole, string[]> = {
  admin: ["查看接口、任务与日志", "管理成员与角色", "发送、重发和撤销邀请"],
  operator: ["查看接口、任务与日志", "执行获授权的日常操作"],
  viewer: ["查看获授权的只读数据"],
};

function formatDate(value?: string | null) {
  if (!value) return "尚未登录";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function MembersPage() {
  const { csrfToken } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole>("viewer");
  const [filter, setFilter] = useState<"all" | UserRole | "invited">("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function loadData() {
    setError("");
    try {
      const [userRows, invitationRows] = await Promise.all([
        api.listUsers(),
        api.listInvitations(),
      ]);
      setUsers(userRows);
      setInvitations(invitationRows);
      setSelectedId((current) => current ?? userRows[0]?.id ?? null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "成员数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const selectedUser = users.find((user) => user.id === selectedId) ?? null;
  useEffect(() => {
    if (selectedUser) setSelectedRole(selectedUser.role);
  }, [selectedUser]);

  const counts = useMemo(
    () => ({
      all: users.length,
      admin: users.filter((user) => user.role === "admin").length,
      operator: users.filter((user) => user.role === "operator").length,
      viewer: users.filter((user) => user.role === "viewer").length,
      invited: users.filter((user) => user.status === "invited").length,
    }),
    [users],
  );
  const activeAdminCount = users.filter(
    (user) => user.role === "admin" && user.status === "active",
  ).length;
  const protectsLastAdmin = Boolean(
    selectedUser?.role === "admin" &&
      selectedUser.status === "active" &&
      activeAdminCount <= 1,
  );
  const filteredUsers = users.filter((user) => {
    const term = search.trim().toLowerCase();
    const matchesSearch =
      !term ||
      user.email.toLowerCase().includes(term) ||
      (user.displayName ?? "").toLowerCase().includes(term);
    const matchesFilter =
      filter === "all" ||
      (filter === "invited" ? user.status === "invited" : user.role === filter);
    return matchesSearch && matchesFilter;
  });
  const selectedInvitation = selectedUser
    ? invitations.find(
        (invitation) =>
          invitation.email === selectedUser.email &&
          !invitation.usedAt &&
          !invitation.revokedAt,
      )
    : undefined;

  async function runMutation(action: () => Promise<unknown>) {
    if (!csrfToken) return;
    setBusy(true);
    setError("");
    try {
      await action();
      await loadData();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "操作失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  async function saveRole() {
    if (!selectedUser || !csrfToken || selectedRole === selectedUser.role) return;
    await runMutation(() => api.updateUser(selectedUser.id, { role: selectedRole }, csrfToken));
  }

  async function toggleStatus() {
    if (!selectedUser || !csrfToken) return;
    const status: UserStatus = selectedUser.status === "disabled" ? "active" : "disabled";
    await runMutation(() => api.updateUser(selectedUser.id, { status }, csrfToken));
  }

  return (
    <AppShell>
      <main className="members-page" data-node-id="46:344">
        <header className="page-heading">
          <div>
            <h1>成员与权限</h1>
            <p>使用固定角色控制敏感操作；角色变更与成员状态由管理员维护。</p>
          </div>
          <button className="primary-button invite-button" type="button" onClick={() => setInviteOpen(true)}>
            ＋&nbsp;&nbsp;邀请成员
          </button>
        </header>

        <section className="role-overview" aria-label="固定角色说明">
          {rolePolicies.map((policy) => (
            <article className={`role-policy role-policy--${policy.role}`} key={policy.role}>
              <span className="role-mark">{policy.mark}</span>
              <div><strong>{roleNames[policy.role]}</strong><b>{policy.title}</b></div>
              <p>{policy.detail}</p>
              <span className="fixed-role">固定角色</span>
            </article>
          ))}
        </section>

        <section className="member-toolbar">
          <input
            aria-label="搜索成员"
            placeholder="搜索姓名或邮箱"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {(["all", "admin", "operator", "viewer", "invited"] as const).map((item) => (
            <button
              className={filter === item ? "active" : ""}
              key={item}
              type="button"
              onClick={() => setFilter(item)}
            >
              {item === "all" ? "全部" : item === "invited" ? "待接受" : roleNames[item]} {counts[item]}
            </button>
          ))}
          <span>固定角色 · 至少保留 1 名可用管理员</span>
        </section>

        {error ? <div className="page-alert" role="alert">{error}</div> : null}
        <section className="member-workspace">
          <div className="member-list">
            <div className="member-list-title"><strong>成员</strong><span>角色为系统固定规则</span></div>
            <div className="member-table-head"><span>成员</span><span>角色</span><span>状态</span><span>最近活动</span></div>
            <div className="member-rows">
              {loading ? <p className="empty-state">正在加载成员…</p> : null}
              {!loading && filteredUsers.length === 0 ? <p className="empty-state">没有符合条件的成员</p> : null}
              {filteredUsers.map((user) => (
                <button
                  className={`member-row ${user.id === selectedId ? "selected" : ""}`}
                  key={user.id}
                  type="button"
                  onClick={() => setSelectedId(user.id)}
                >
                  <span className="member-identity">
                    <i>{(user.displayName ?? user.email).slice(0, 1)}</i>
                    <span><strong>{user.displayName ?? "待接受邀请"}</strong><small>{user.email}</small></span>
                  </span>
                  <span className={`badge role-${user.role}`}>{roleNames[user.role]}</span>
                  <span className={`badge status-${user.status}`}>{statusNames[user.status]}</span>
                  <span className="last-seen">{formatDate(user.lastLoginAt)}</span>
                </button>
              ))}
            </div>
          </div>

          <aside className="member-detail">
            {selectedUser ? (
              <>
                <div className="detail-heading">
                  <span className={`badge status-${selectedUser.status}`}>{statusNames[selectedUser.status]}</span>
                  <h2>{selectedUser.displayName ?? "待接受邀请"}</h2>
                  <p>{selectedUser.email}</p>
                  <small>最近活动：{formatDate(selectedUser.lastLoginAt)}</small>
                </div>
                <div className="detail-tabs"><span>成员信息</span><b>权限矩阵</b><span>邀请状态</span></div>
                <div className="permission-card">
                  <h3>{roleNames[selectedUser.role]}权限</h3>
                  <ul>{permissions[selectedUser.role].map((item) => <li key={item}>✓&nbsp;&nbsp;{item}</li>)}</ul>
                </div>
                <div className="role-editor">
                  <label htmlFor="member-role">当前角色</label>
                  <div>
                    <select
                      disabled={protectsLastAdmin || busy}
                      id="member-role"
                      value={selectedRole}
                      onChange={(event) => setSelectedRole(event.target.value as UserRole)}
                    >
                      <option value="admin">管理员</option>
                      <option value="operator">操作员</option>
                      <option value="viewer">只读成员</option>
                    </select>
                    <button className="primary-button" disabled={busy || selectedRole === selectedUser.role} type="button" onClick={saveRole}>保存角色</button>
                  </div>
                </div>
                {selectedInvitation ? (
                  <div className="invitation-actions">
                    <span>邀请将在 {formatDate(selectedInvitation.expiresAt)} 过期</span>
                    <div>
                      <button disabled={busy} type="button" onClick={() => runMutation(() => api.resendInvitation(selectedInvitation.id, csrfToken!))}>重新发送</button>
                      <button className="danger-link" disabled={busy} type="button" onClick={() => runMutation(() => api.revokeInvitation(selectedInvitation.id, csrfToken!))}>撤销邀请</button>
                    </div>
                  </div>
                ) : null}
                <div className="member-danger-row">
                  <span>{protectsLastAdmin ? "至少保留 1 名可用管理员" : "状态修改会立即影响登录"}</span>
                  <button
                    className="danger-button"
                    disabled={busy || protectsLastAdmin || selectedUser.status === "invited"}
                    type="button"
                    onClick={toggleStatus}
                  >
                    {selectedUser.status === "disabled" ? "启用成员" : "停用成员"}
                  </button>
                </div>
              </>
            ) : <p className="empty-state">请选择成员</p>}
          </aside>
        </section>
      </main>
      {inviteOpen ? (
        <InviteMemberModal
          busy={busy}
          onClose={() => setInviteOpen(false)}
          onSubmit={async (email, role) => {
            if (!csrfToken) return;
            await runMutation(() => api.createInvitation(email, role, csrfToken));
            setInviteOpen(false);
          }}
        />
      ) : null}
    </AppShell>
  );
}

function InviteMemberModal({
  busy,
  onClose,
  onSubmit,
}: {
  busy: boolean;
  onClose: () => void;
  onSubmit: (email: string, role: UserRole) => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("operator");
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(email, role);
  }
  return (
    <Modal title="邀请成员" onClose={onClose}>
      <p className="modal-description">系统将向该邮箱发送一次性注册链接。</p>
      <form className="invite-form" onSubmit={handleSubmit}>
        <FormField
          autoFocus
          id="invite-email"
          label="邮箱"
          placeholder="name@example.com"
          required
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <label className="form-field" htmlFor="invite-role">
          <span>角色</span>
          <select id="invite-role" value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
            <option value="admin">管理员</option>
            <option value="operator">操作员</option>
            <option value="viewer">只读成员</option>
          </select>
        </label>
        <p className="invite-note">邀请有效期 24 小时；过期后可由管理员重新发送。</p>
        <div className="modal-actions">
          <button className="neutral-button" type="button" onClick={onClose}>取消</button>
          <button className="primary-button" disabled={busy} type="submit">{busy ? "发送中…" : "发送邀请"}</button>
        </div>
      </form>
    </Modal>
  );
}
