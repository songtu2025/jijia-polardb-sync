export type UserRole = "admin" | "operator" | "viewer";
export type UserStatus = "invited" | "active" | "disabled";

export interface User {
  id: number;
  email: string;
  displayName: string | null;
  role: UserRole;
  status: UserStatus;
  lastLoginAt?: string | null;
  createdAt?: string;
}

export interface AuthResult {
  user: User;
  csrfToken: string;
}

export interface InvitationValidation {
  email: string;
  role: UserRole;
  expiresAt: string;
}

export interface Invitation {
  id: number;
  email: string;
  role: UserRole;
  expiresAt: string;
  usedAt: string | null;
  revokedAt: string | null;
}
