/**
 * 本地状态 store（本地自用模式）。
 *
 * 原先这里有登录/注册/验码/领额度等一整套付费流程，现已全部移除：
 * 本地自用模式下后端恒返回「已登录 + 不限量」，只需要一个只读状态供界面展示。
 */
import { create } from "zustand";
import { subscriptionApi, getSubscriptionError, type SubscriptionStatus } from "@/api/subscription";

interface SubscriptionState {
  status: SubscriptionStatus | null;
  loading: boolean;
  error: string;
  fetchStatus: () => Promise<SubscriptionStatus | null>;
}

export const useSubscriptionStore = create<SubscriptionState>((set) => ({
  status: null,
  loading: false,
  error: "",
  fetchStatus: async () => {
    set({ loading: true, error: "" });
    try {
      const status = await subscriptionApi.getStatus();
      set({ status, loading: false });
      return status;
    } catch (error: any) {
      set({ error: getSubscriptionError(error), loading: false });
      return null;
    }
  },
}));
