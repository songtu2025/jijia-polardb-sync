import type {
  AuthResult,
  Invitation,
  InvitationValidation,
  User,
  UserRole,
  UserStatus,
} from "./types";

interface SuccessResponse<T> {
  data: T;
  requestId: string;
}

interface ErrorResponse {
  error?: {
    code?: string;
    message?: string;
  };
  requestId?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  csrfToken?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(path, {
    ...options,
    credentials: "include",
    headers,
  });
  const responseText = await response.text();
  let payload = {} as SuccessResponse<T> & ErrorResponse;
  if (responseText) {
    try {
      payload = JSON.parse(responseText) as SuccessResponse<T> & ErrorResponse;
    } catch {
      // 代理或网关错误不一定返回 JSON，统一转换成可展示的 API 错误。
    }
  }
  if (!response.ok) {
    throw new ApiError(
      payload.error?.message ?? "请求失败，请稍后重试",
      response.status,
      payload.error?.code ?? "REQUEST_FAILED",
      payload.requestId,
    );
  }
  return payload.data;
}

export const api = {
  session: () => request<AuthResult>("/api/v1/auth/session"),
  login: (email: string, password: string) =>
    request<AuthResult>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: (csrfToken: string) =>
    request<{ loggedOut: boolean }>(
      "/api/v1/auth/logout",
      { method: "POST" },
      csrfToken,
    ),
  validateInvitation: (token: string) =>
    request<InvitationValidation>("/api/v1/auth/invitations/validate", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  register: (token: string, displayName: string, password: string) =>
    request<AuthResult>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ token, display_name: displayName, password }),
    }),
  listUsers: () => request<User[]>("/api/v1/users"),
  updateUser: (
    userId: number,
    changes: { role?: UserRole; status?: UserStatus },
    csrfToken: string,
  ) =>
    request<User>(
      `/api/v1/users/${userId}`,
      { method: "PATCH", body: JSON.stringify(changes) },
      csrfToken,
    ),
  listInvitations: () => request<Invitation[]>("/api/v1/invitations"),
  createInvitation: (email: string, role: UserRole, csrfToken: string) =>
    request<Invitation>(
      "/api/v1/invitations",
      { method: "POST", body: JSON.stringify({ email, role }) },
      csrfToken,
    ),
  resendInvitation: (invitationId: number, csrfToken: string) =>
    request<Invitation>(
      `/api/v1/invitations/${invitationId}/resend`,
      { method: "POST" },
      csrfToken,
    ),
  revokeInvitation: (invitationId: number, csrfToken: string) =>
    request<Invitation>(
      `/api/v1/invitations/${invitationId}/revoke`,
      { method: "POST" },
      csrfToken,
    ),
};
