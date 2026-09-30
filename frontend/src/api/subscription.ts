import client from "./client";

export type UserType = "guest" | "registered" | "subscribed";

export interface UserInfo {
  id?: string | number;
  user_id?: string | number;
  username?: string;
  email?: string;
  phone?: string;
  nickname?: string;
  is_active?: boolean;
  created_at?: string;
  last_login?: string;
  [key: string]: any;
}

export interface Entitlement {
  id?: string | number;
  software_id?: string;
  softwareId?: string;
  software_code?: string;
  softwareCode?: string;
  status?: string;
  state?: string;
  valid_until?: string;
  validUntil?: string;
  expire_at?: string;
  expires_at?: string;
  device_limit?: number;
  bound_device_count?: number;
  boundDeviceCount?: number;
  remaining_points?: number;
  points?: number;
  total_points?: number;
  quota_remaining?: number;
  balance?: number;
  last_granted_at?: string;
  [key: string]: any;
}

export interface SubscriptionLinks {
  products: string;
  home: string;
  versions: string;
}

export interface SubscriptionStatus {
  software_id: string;
  self_use?: boolean;
  is_logged_in: boolean;
  user_type: UserType;
  user_info: UserInfo | null;
  entitlements: Entitlement[];
  active_entitlement: Entitlement | null;
  daily_usage: number;
  daily_limit: number | null;
  remaining_today: number | null;
  can_create_task: boolean;
  daily_node_usage?: number;
  daily_node_limit?: number | null;
  remaining_nodes_today?: number | null;
  can_execute_node?: boolean;
  /** 非订阅用户当天是否还能领取免费额度（前端「领取额度」按钮的显示条件） */
  can_claim_quota?: boolean;
  /** 预计可领取数量（当日上限 − 当日已领批次累计） */
  claimable_count?: number;
  /** 当日云端已发放的额度累计（签名值） */
  quota_granted_total?: number;
  links: SubscriptionLinks;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email: string;
  phone?: string;
  verification_code?: string;
}

export interface ResetPasswordPayload {
  email: string;
  code: string;
  new_password: string;
}

export function getSubscriptionError(error: any) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || "操作失败";
}

export function isDeviceLimitError(error: any) {
  const text = String(getSubscriptionError(error) || "");
  return text.includes("1205") || text.includes("设备数量已超过限制") || text.includes("设备超限");
}

export function isSubscriptionBlocked(error: any) {
  const status = error?.status ?? error?.response?.status;
  return status === 402 || status === 403;
}

export function getQuotaExhaustedMessage(status: SubscriptionStatus | null) {
  if (status?.self_use) return "本地自用模式未设置任务额度，请检查工作流和服务配置。";
  return "当前任务不可执行，请检查服务状态或接口配置。";
}

/**
 * 本地预校验发现额度不足时，通知后端向头部通知中心写入一条系统提醒。
 * 后端会再次校验额度并按天去重，失败时静默忽略，不阻塞用户操作。
 */
export function notifyQuotaExhausted() {
  return client.post("/api/subscription/quota-notice").catch(() => undefined);
}

export const subscriptionApi = {
  getStatus: () => client.get("/api/subscription/status").then((r) => r.data as SubscriptionStatus),
  refresh: () => client.post("/api/subscription/refresh").then((r) => r.data as SubscriptionStatus),
  login: (data: LoginPayload) => client.post("/api/subscription/login", data).then((r) => r.data as SubscriptionStatus),
  logout: () => client.post("/api/subscription/logout").then((r) => r.data),
  unbindDevice: () => client.post("/api/subscription/unbind-device").then((r) => r.data as SubscriptionStatus),
  register: (data: RegisterPayload) => client.post("/api/subscription/register", data).then((r) => r.data),
  sendCode: (email: string) => client.post("/api/subscription/send-code", { email }).then((r) => r.data),
  sendResetCode: (email: string) => client.post("/api/subscription/reset-password/send-code", { email }).then((r) => r.data),
  resetPassword: (data: ResetPasswordPayload) => client.post("/api/subscription/reset-password/confirm", data).then((r) => r.data),
  verifyCard: (card_code: string) => client.post("/api/subscription/verify-card", { card_code }).then((r) => r.data as SubscriptionStatus),
  claimQuota: () => client.post("/api/subscription/claim-quota").then((r) => r.data),
  getLinks: () => client.get("/api/subscription/links").then((r) => r.data as SubscriptionLinks),
};
