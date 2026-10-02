const MANAGER_BASE = "http://localhost:18001";

const hasLocalManager = () => window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

export const managerApi = {
  restartControlPlaneWorker: () =>
    !hasLocalManager()
      ? Promise.reject(new Error("Docker 部署不提供桌面进程管理器"))
      :
    fetch(`${MANAGER_BASE}/manager/restart-control-plane-worker`, { method: "POST" }).then(
      async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || data.message || `重启请求失败 (${res.status})`);
        }
        return res.json();
      },
    ),
};
