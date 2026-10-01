/**
 * 本地自用模式的「状态」接口。
 *
 * 付费相关内容（注册、卡密、积分、设备绑定、每日额度领取、购买链接）已全部移除。
 * 后端恒返回「已登录 + 不限量」，这里保留一层薄封装只为给执行前的本地预校验一个统一出口。
 *
 * 账号登录/登出走 control-plane 的本地用户名密码接口（见 api/controlPlane.ts）。
 */
import client from "./client";

export interface SubscriptionStatus {
  software_id: string;
  /** 恒为 true：本地自用模式 */
  self_use?: boolean;
  is_logged_in: boolean;
  user_info: { username?: string; [key: string]: any } | null;
  /** 恒为 null：不限量 */
  daily_limit: number | null;
  daily_node_limit?: number | null;
  can_create_task: boolean;
  can_execute_node?: boolean;
}

export function getSubscriptionError(error: any) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || "操作失败";
}

export const subscriptionApi = {
  getStatus: () => client.get("/api/subscription/status").then((r) => r.data as SubscriptionStatus),
};
